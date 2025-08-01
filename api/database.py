import json
import logging
import os
from typing import Dict, List, Optional

import pymysql
from dotenv import load_dotenv
from models import Recipe
from pymysql import err as pymysql_err

# Load environment variables
load_dotenv()
MARIADB_HOST = "mariadb"
MARIADB_PORT = 3306
MARIADB_USER = os.getenv("MARIADB_USER")
MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD")
MARIADB_DATABASE = os.getenv("MARIADB_DATABASE")


# Configure logging
logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.db_config = {
            "host": MARIADB_HOST,
            "port": MARIADB_PORT,
            "user": MARIADB_USER,
            "password": MARIADB_PASSWORD,
            "database": MARIADB_DATABASE,
            "cursorclass": pymysql.cursors.DictCursor,
        }

    def get_connection(self):
        """Get a database connection"""
        return pymysql.connect(**self.db_config)

    def create_user_if_not_exists(
        self, user_id: str, email: str, name: str, image_url: Optional[str] = None
    ) -> bool:
        """Create a user if they don't exist"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                existing_user = cursor.fetchone()
                if existing_user:
                    return False

                cursor.execute(
                    "INSERT INTO users (id, email, name, image_url) VALUES (%s, %s, %s, %s)",
                    (user_id, email, name, image_url),
                )
                conn.commit()
                logger.info(
                    f"Added User<user_id={user_id}, email={email}, name={name}> to the database"
                )
                return True

    def delete_user(self, user_id: str) -> bool:
        """Delete a user from the database. Related data is deleted via ON DELETE CASCADE."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
                logger.info(f"Deleted user and related data for user_id={user_id}")
                return True

    def save_recommendations(self, user_id: str, new_recipe_ids: List[str]) -> bool:
        """Save multiple recommendations to the database in order"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for recipe_id in new_recipe_ids:
                    cursor.execute(
                        "INSERT INTO recommendations (user_id, recipe_id) VALUES (%s, %s)",
                        (user_id, recipe_id),
                    )
                conn.commit()
                return True

    def get_recommendations(self, user_id: str, count: int = 10) -> List[str]:
        """Get recommendations for a user"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT recipe_id FROM recommendations WHERE user_id = %s ORDER BY id ASC LIMIT %s",
                    (user_id, count),
                )
                recommendations = cursor.fetchall()
                return [rec["recipe_id"] for rec in recommendations]

    def remove_recommendation(self, user_id: str, recipe_id: str) -> bool:
        """Remove a recommendation from the database. This should be done when the user provides feedback about
        a recipe."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM recommendations WHERE user_id = %s AND recipe_id = %s",
                    (user_id, recipe_id),
                )
                conn.commit()
                return True

    def save_feedback(self, user_id: str, recipe_id: str, feedback_type: str) -> bool:
        """Save user feedback for a recipe"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO user_feedback (user_id, recipe_id, feedback_type) VALUES (%s, %s, %s)",
                    (user_id, recipe_id, feedback_type),
                )
                conn.commit()
                return True

    def get_feedback(self, user_id: str) -> Dict[str, List[str]]:
        """Get all feedback for a user, separated by type"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT recipe_id, feedback_type FROM user_feedback WHERE user_id = %s",
                    (user_id,),
                )
                feedback = cursor.fetchall()

                liked_recipes = [
                    f["recipe_id"] for f in feedback if f["feedback_type"] == "like"
                ]
                disliked_recipes = [
                    f["recipe_id"] for f in feedback if f["feedback_type"] == "dislike"
                ]

                return {"liked": liked_recipes, "disliked": disliked_recipes}

    def get_saved_recipes(self, user_id: str) -> List[str]:
        """Get all saved recipe IDs for a user"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT recipe_id FROM user_saved_recipes WHERE user_id = %s ORDER BY saved_at DESC",
                    (user_id,),
                )
                saved_recipes = cursor.fetchall()
                return [recipe["recipe_id"] for recipe in saved_recipes]

    def save_recipe(self, user_id: str, recipe_id: str) -> bool:
        """Save a recipe for a user"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(
                        "INSERT INTO user_saved_recipes (user_id, recipe_id) VALUES (%s, %s)",
                        (user_id, recipe_id),
                    )
                    conn.commit()
                    logger.info(f"User {user_id} saved recipe {recipe_id}")
                    return True
                except pymysql_err.IntegrityError:
                    # Recipe already saved by this user
                    logger.info(f"Recipe {recipe_id} already saved by user {user_id}")
                    return False

    def unsave_recipe(self, user_id: str, recipe_id: str) -> bool:
        """Remove a saved recipe for a user"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM user_saved_recipes WHERE user_id = %s AND recipe_id = %s",
                    (user_id, recipe_id),
                )
                conn.commit()
                affected_rows = cursor.rowcount
                if affected_rows > 0:
                    logger.info(f"User {user_id} unsaved recipe {recipe_id}")
                    return True
                else:
                    logger.info(f"Recipe {recipe_id} was not saved by user {user_id}")
                    return False

    def get_recipe(self, recipe_id: str) -> Recipe:
        """Get recipe data from the database"""
        recipes = self.get_multiple_recipes([recipe_id])
        return recipes[0] if recipes else None

    def get_multiple_recipes(self, recipe_ids: List[str]) -> List[Recipe]:
        """Get multiple recipes from the database in a single query"""
        if not recipe_ids:
            return []

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Create placeholders for the IN clause
                placeholders = ", ".join(["%s"] * len(recipe_ids))
                cursor.execute(
                    f"""SELECT id, title, description, recipe_url, image_url, ingredients, instructions, 
                    category, cuisine, site_name, keywords, dietary_restrictions, total_time, overall_rating 
                    FROM recipes WHERE id IN ({placeholders})""",
                    recipe_ids,
                )
                recipes = cursor.fetchall()

                # Convert recipe fields from JSON str to arrays and create Recipe objects
                recipe_objects = []
                for recipe in recipes:
                    if recipe:
                        recipe["ingredients"] = json.loads(recipe["ingredients"])
                        recipe["instructions"] = json.loads(recipe["instructions"])
                        recipe["keywords"] = json.loads(recipe["keywords"])
                        recipe["dietary_restrictions"] = json.loads(
                            recipe["dietary_restrictions"]
                        )
                        recipe_objects.append(Recipe(**recipe))

                return recipe_objects

    def get_all_recipe_ids(self) -> List[str]:
        """Get all recipe ids from the database"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM recipes")
                res = cursor.fetchall()

                # Convert recipe_ids from [{id: recipe_id}] to [recipe_id]
                recipe_ids = []
                for dict_ in res:
                    recipe_ids.append(dict_["id"])

                return recipe_ids

    def get_all_recipe_titles(self) -> Dict[str, str]:
        """Get all recipe titles from the database. This is used for logging/debug purposes"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, title FROM recipes")
                res = cursor.fetchall()
                return {dict_["id"]: dict_["title"] for dict_ in res}

    def add_multiple_recipes(self, recipes_data: List[Dict]) -> List[str]:
        """
        Add multiple recipes to the database efficiently using batch insert

        Args:
            recipes_data: List of dictionaries containing recipe information

        Returns:
            List[str]: List of recipe IDs that were successfully added
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                recipe_ids = []
                for recipe_data in recipes_data:
                    try:
                        cursor.execute(
                            """
                            INSERT INTO recipes (
                                id, title, description, recipe_url, image_url, ingredients, instructions,
                                category, cuisine, site_name, keywords, dietary_restrictions,
                                total_time, overall_rating
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                recipe_data["id"],
                                recipe_data["title"],
                                recipe_data["description"],
                                recipe_data["recipe_url"],
                                recipe_data["image_url"],
                                recipe_data["ingredients"],
                                recipe_data["instructions"],
                                recipe_data["category"],
                                recipe_data["cuisine"],
                                recipe_data["site_name"],
                                recipe_data["keywords"],
                                recipe_data["dietary_restrictions"],
                                recipe_data["total_time"],
                                recipe_data["overall_rating"],
                            ),
                        )
                        recipe_ids.append(recipe_data["id"])
                    except pymysql_err.IntegrityError as e:
                        if e.args[0] == 1062:  # Duplicate entry error
                            logger.warning(
                                f"Recipe with ID {recipe_data['id']} already exists, skipping"
                            )
                            continue
                        else:
                            raise
                    except Exception as e:
                        logger.error(f"Error adding recipe {recipe_data['id']}: {e}")
                        continue

                conn.commit()
                logger.info(f"Successfully added {len(recipe_ids)} recipes to database")
                return recipe_ids

    def recipe_exists(self, recipe_id: str) -> bool:
        """Check if a recipe exists in the database"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM recipes WHERE id = %s", (recipe_id,)
                )
                count = cursor.fetchone()["COUNT(*)"]
                return count > 0
