import json
import logging
import os
from typing import Dict, List, Optional

import pymysql
from dotenv import load_dotenv
from models import Recipe

# Load environment variables
load_dotenv()
MARIADB_HOST = os.getenv("MARIADB_HOST")
MARIADB_PORT = os.getenv("MARIADB_PORT")
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

    def get_recipe_data(self, recipe_id: str) -> Recipe:
        """Get recipe data from the database"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """SELECT id, title, description, recipe_url, image_url, ingredients, instructions, 
                    category, cuisine, site_name, keywords, dietary_restrictions, total_time, overall_rating 
                    FROM recipes WHERE id = %s""",
                    (recipe_id,),
                )
                recipe = cursor.fetchone()

                # Convert recipe fields from JSON str to arrays
                recipe["ingredients"] = json.loads(recipe["ingredients"])
                recipe["instructions"] = json.loads(recipe["instructions"])
                recipe["keywords"] = json.loads(recipe["keywords"])
                recipe["dietary_restrictions"] = json.loads(
                    recipe["dietary_restrictions"]
                )

                return Recipe(**recipe)

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

    def get_all_feature_vectors(self) -> Dict[str, float]:
        """Get all feature vectors from the database"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, feature_vector FROM recipes")
                res = cursor.fetchall()

                # Convert feature vectors from [{"id": id, "feature_vector": feature_vector}] to {id: feature_vector}
                id_vec_map = {}
                for dict_ in res:
                    id_ = dict_["id"]
                    vec = dict_["feature_vector"]
                    id_vec_map[id_] = vec

                return id_vec_map


# TODO: Test all functions with mock data
