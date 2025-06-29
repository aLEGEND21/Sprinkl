# database.py - Database management for the recipe recommendation API
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.db_config = {
            "host": os.getenv("MARIADB_HOST", "localhost"),
            "port": int(os.getenv("MARIADB_PORT", "3306")),
            "user": os.getenv("MARIADB_USER", "root"),
            "password": os.getenv("MARIADB_PASSWORD"),
            "database": os.getenv("MARIADB_DATABASE", "foodapp_db"),
            "charset": "utf8mb4",
        }

    def get_connection(self):
        """Get a database connection"""
        return pymysql.connect(**self.db_config)

    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute(
            """
            SELECT id, email, name, image_url, created_at, updated_at
            FROM users 
            WHERE id = %s
        """,
            (user_id,),
        )

        user = cursor.fetchone()
        cursor.close()
        conn.close()

        return user

    async def create_user_if_not_exists(
        self, user_id: str, email: str, name: str, image_url: Optional[str] = None
    ) -> bool:
        """Create a new user if they don't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if the user already exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        existing_user = cursor.fetchone()

        if existing_user:
            logger.info(f"User {user_id} already exists")
            return False

        # If the user doesn't exist, create them
        cursor.execute(
            """
            INSERT INTO users (id, email, name, image_url, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (user_id, email, name, image_url, datetime.now(), datetime.now()),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    async def submit_feedback(
        self, user_id: str, recipe_id: str, feedback_type: str
    ) -> bool:
        """Submit user feedback for a recipe"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Insert or update feedback
        cursor.execute(
            """
            INSERT INTO user_feedback (user_id, recipe_id, feedback_type, timestamp)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            feedback_type = VALUES(feedback_type),
            timestamp = VALUES(timestamp)
        """,
            (user_id, recipe_id, feedback_type, datetime.now()),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    async def get_user_feedback(self, user_id: str) -> Dict[str, List[str]]:
        """Get all feedback for a user"""
        conn = self.get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute(
            """
            SELECT recipe_id, feedback_type 
            FROM user_feedback 
            WHERE user_id = %s
        """,
            (user_id,),
        )

        feedback = cursor.fetchall()

        liked_recipes = [
            f["recipe_id"] for f in feedback if f["feedback_type"] == "like"
        ]
        disliked_recipes = [
            f["recipe_id"] for f in feedback if f["feedback_type"] == "dislike"
        ]

        cursor.close()
        conn.close()

        return {"liked": liked_recipes, "disliked": disliked_recipes}

    async def get_recipe_by_id(self, recipe_id: str) -> Optional[Dict]:
        """Get a recipe by ID"""
        res = await self.get_recipes_by_ids([recipe_id])
        return res[0] if res else None

    async def get_recipes_by_ids(self, recipe_ids: List[str]) -> List[Dict]:
        """Get recipes by IDs"""
        if not recipe_ids:
            return []

        conn = self.get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Create placeholders for the IN clause
        placeholders = ",".join(["%s"] * len(recipe_ids))
        cursor.execute(
            f"""
            SELECT id, title, description, recipe_url, image_url, ingredients, instructions,
                   category, cuisine, site_name, keywords, dietary_restrictions,
                   total_time, overall_rating
            FROM recipes 
            WHERE id IN ({placeholders})
            """,
            tuple(recipe_ids),  # Convert list to tuple for proper parameter expansion
        )

        recipes = cursor.fetchall()
        cursor.close()
        conn.close()

        # Parse JSON fields
        for recipe in recipes:
            if recipe["ingredients"]:
                try:
                    recipe["ingredients"] = json.loads(recipe["ingredients"])
                except json.JSONDecodeError:
                    recipe["ingredients"] = []

            if recipe["instructions"]:
                try:
                    recipe["instructions"] = json.loads(recipe["instructions"])
                except json.JSONDecodeError:
                    recipe["instructions"] = []

            if recipe["keywords"]:
                try:
                    recipe["keywords"] = json.loads(recipe["keywords"])
                except json.JSONDecodeError:
                    recipe["keywords"] = []

            if recipe["dietary_restrictions"]:
                try:
                    recipe["dietary_restrictions"] = json.loads(
                        recipe["dietary_restrictions"]
                    )
                except json.JSONDecodeError:
                    recipe["dietary_restrictions"] = []

        return recipes

    async def save_recommendations(self, user_id: str, recipe_ids: List[str]) -> bool:
        """Save recommendations to the database"""
        conn = self.get_connection()
        cursor = conn.cursor()

        recommendations_json = json.dumps(recipe_ids)

        cursor.execute(
            """
            INSERT INTO recommendations (user_id, recommended_recipe_ids, last_updated)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            recommended_recipe_ids = VALUES(recommended_recipe_ids),
            last_updated = VALUES(last_updated)
        """,
            (user_id, recommendations_json, datetime.now()),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    async def get_saved_recommendations(self, user_id: str) -> List[str]:
        """Get saved recommendations for a user"""
        conn = self.get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute(
            """
            SELECT recommended_recipe_ids, last_updated
            FROM recommendations 
            WHERE user_id = %s
        """,
            (user_id,),
        )

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result and result["recommended_recipe_ids"]:
            try:
                return json.loads(result["recommended_recipe_ids"])
            except json.JSONDecodeError:
                return []

        return []

    async def search_recipes(
        self,
        query: Optional[str] = None,
        cuisine: Optional[str] = None,
        max_time: Optional[int] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """Search recipes with filters"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            # Build query
            sql = """
                SELECT id, title, description, recipe_url, image_url, ingredients, instructions,
                       category, cuisine, site_name, keywords, dietary_restrictions,
                       total_time, overall_rating
                FROM recipes 
                WHERE 1=1
            """
            params = []

            if query:
                sql += " AND (title LIKE %s OR description LIKE %s OR instructions LIKE %s)"
                params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])

            if cuisine:
                sql += " AND cuisine = %s"
                params.append(cuisine)

            if max_time:
                sql += " AND total_time <= %s"
                params.append(max_time)

            sql += " ORDER BY title LIMIT %s"
            params.append(limit)

            cursor.execute(sql, params)
            recipes = cursor.fetchall()

            # Parse JSON fields
            for recipe in recipes:
                if recipe["ingredients"]:
                    try:
                        recipe["ingredients"] = json.loads(recipe["ingredients"])
                    except json.JSONDecodeError:
                        recipe["ingredients"] = []

                if recipe["instructions"]:
                    try:
                        recipe["instructions"] = json.loads(recipe["instructions"])
                    except json.JSONDecodeError:
                        recipe["instructions"] = []

                if recipe["keywords"]:
                    try:
                        recipe["keywords"] = json.loads(recipe["keywords"])
                    except json.JSONDecodeError:
                        recipe["keywords"] = []

                if recipe["dietary_restrictions"]:
                    try:
                        recipe["dietary_restrictions"] = json.loads(
                            recipe["dietary_restrictions"]
                        )
                    except json.JSONDecodeError:
                        recipe["dietary_restrictions"] = []

            cursor.close()
            conn.close()
            return recipes

        except Exception as e:
            logger.error(f"Error searching recipes: {str(e)}")
            return []


def get_database_connection():
    """Factory function to get database connection"""
    return DatabaseManager().get_connection()
