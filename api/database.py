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
        try:
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

        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None

    async def create_user(
        self, 
        user_id: str, 
        email: str, 
        name: str, 
        image_url: Optional[str] = None
    ) -> bool:
        """Create a new user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

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

        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return False

    async def update_user(
        self, 
        user_id: str, 
        email: str, 
        name: str, 
        image_url: Optional[str] = None
    ) -> bool:
        """Update an existing user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE users 
                SET email = %s, name = %s, image_url = %s, updated_at = %s
                WHERE id = %s
            """,
                (email, name, image_url, datetime.now(), user_id),
            )

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return False

    async def ensure_user_exists(self, user_id: str) -> bool:
        """Ensure a user exists in the database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if cursor.fetchone():
                return True

            # Create user if doesn't exist
            cursor.execute("INSERT INTO users (id) VALUES (%s)", (user_id,))
            conn.commit()

            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error ensuring user exists: {str(e)}")
            return False

    async def submit_feedback(
        self, user_id: str, recipe_id: str, feedback_type: str
    ) -> bool:
        """Submit user feedback for a recipe"""
        try:
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

        except Exception as e:
            logger.error(f"Error submitting feedback: {str(e)}")
            return False

    async def get_user_feedback(self, user_id: str) -> Dict[str, List[str]]:
        """Get all feedback for a user"""
        try:
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

        except Exception as e:
            logger.error(f"Error getting user feedback: {str(e)}")
            return {"liked": [], "disliked": []}

    async def get_recipe_by_id(self, recipe_id: str) -> Optional[Dict]:
        """Get a recipe by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            cursor.execute(
                """
                SELECT id, recipe_name, ingredient_measurements, time_mins, cuisine,
                       instructions, recipe_url, ingredient_list, image_url, ingredient_count
                FROM recipes 
                WHERE id = %s
            """,
                (recipe_id,),
            )

            recipe = cursor.fetchone()
            cursor.close()
            conn.close()

            if recipe:
                # Parse JSON fields
                if recipe["ingredient_list"]:
                    try:
                        recipe["ingredient_list"] = json.loads(
                            recipe["ingredient_list"]
                        )
                    except json.JSONDecodeError:
                        recipe["ingredient_list"] = []

                return recipe

            return None

        except Exception as e:
            logger.error(f"Error getting recipe by ID: {str(e)}")
            return None

    async def search_recipes(
        self,
        query: Optional[str] = None,
        cuisine: Optional[str] = None,
        max_time_mins: Optional[int] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """Search recipes with filters"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            # Build query
            sql = """
                SELECT id, recipe_name, ingredient_measurements, time_mins, cuisine,
                       instructions, recipe_url, ingredient_list, image_url, ingredient_count
                FROM recipes 
                WHERE 1=1
            """
            params = []

            if query:
                sql += " AND (recipe_name LIKE %s OR instructions LIKE %s)"
                params.extend([f"%{query}%", f"%{query}%"])

            if cuisine:
                sql += " AND cuisine = %s"
                params.append(cuisine)

            if max_time_mins:
                sql += " AND time_mins <= %s"
                params.append(max_time_mins)

            sql += " ORDER BY recipe_name LIMIT %s"
            params.append(limit)

            cursor.execute(sql, params)
            recipes = cursor.fetchall()

            # Parse JSON fields
            for recipe in recipes:
                if recipe["ingredient_list"]:
                    try:
                        recipe["ingredient_list"] = json.loads(
                            recipe["ingredient_list"]
                        )
                    except json.JSONDecodeError:
                        recipe["ingredient_list"] = []

            cursor.close()
            conn.close()
            return recipes

        except Exception as e:
            logger.error(f"Error searching recipes: {str(e)}")
            return []

    async def get_user_stats(self, user_id: str) -> Dict:
        """Get user statistics"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            # Get feedback counts
            cursor.execute(
                """
                SELECT 
                    SUM(CASE WHEN feedback_type = 'like' THEN 1 ELSE 0 END) as total_likes,
                    SUM(CASE WHEN feedback_type = 'dislike' THEN 1 ELSE 0 END) as total_dislikes
                FROM user_feedback 
                WHERE user_id = %s
            """,
                (user_id,),
            )

            counts = cursor.fetchone()
            total_likes = counts["total_likes"] or 0
            total_dislikes = counts["total_dislikes"] or 0

            # Get favorite cuisines
            cursor.execute(
                """
                SELECT r.cuisine, COUNT(*) as like_count
                FROM user_feedback uf
                JOIN recipes r ON uf.recipe_id = r.id
                WHERE uf.user_id = %s AND uf.feedback_type = 'like' AND r.cuisine IS NOT NULL
                GROUP BY r.cuisine
                ORDER BY like_count DESC
                LIMIT 5
            """,
                (user_id,),
            )

            favorite_cuisines = [
                {"cuisine": row["cuisine"], "like_count": row["like_count"]}
                for row in cursor.fetchall()
            ]

            # Get average cooking time of liked recipes
            cursor.execute(
                """
                SELECT AVG(r.time_mins) as avg_time
                FROM user_feedback uf
                JOIN recipes r ON uf.recipe_id = r.id
                WHERE uf.user_id = %s AND uf.feedback_type = 'like' AND r.time_mins IS NOT NULL
            """,
                (user_id,),
            )

            avg_time_result = cursor.fetchone()
            avg_cooking_time = (
                avg_time_result["avg_time"] if avg_time_result["avg_time"] else None
            )

            cursor.close()
            conn.close()

            return {
                "user_id": user_id,
                "total_likes": total_likes,
                "total_dislikes": total_dislikes,
                "favorite_cuisines": favorite_cuisines,
                "avg_cooking_time": avg_cooking_time,
            }

        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return {
                "user_id": user_id,
                "total_likes": 0,
                "total_dislikes": 0,
                "favorite_cuisines": [],
                "avg_cooking_time": None,
            }

    async def save_recommendations(self, user_id: str, recipe_ids: List[str]) -> bool:
        """Save recommendations to the database"""
        try:
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

        except Exception as e:
            logger.error(f"Error saving recommendations: {str(e)}")
            return False

    async def get_saved_recommendations(self, user_id: str) -> List[str]:
        """Get saved recommendations for a user"""
        try:
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

        except Exception as e:
            logger.error(f"Error getting saved recommendations: {str(e)}")
            return []


def get_database_connection():
    """Factory function to get database connection"""
    return DatabaseManager().get_connection()
