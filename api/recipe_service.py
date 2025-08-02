# recipe_service.py - Service for adding new recipes
import json
import logging
from typing import Dict, List, Optional

from database import DatabaseManager
from dotenv import load_dotenv
from es_service import ElasticsearchService

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class RecipeService:
    def __init__(
        self,
        db_manager: DatabaseManager,
        es_service: ElasticsearchService,
    ):
        """Initialize the RecipeService with database manager and elasticsearch service"""
        self.db_manager = db_manager
        self.es_service = es_service

    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to int, return None if conversion fails"""
        try:
            return int(float(value)) if value and value != "" else None
        except (ValueError, TypeError):
            return None

    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float, return None if conversion fails"""
        try:
            return float(value) if value and value != "" else None
        except (ValueError, TypeError):
            return None

    def _safe_string(self, value) -> str:
        """Safely convert value to string, return empty string if None"""
        return str(value) if value is not None else ""

    def add_recipe(self, recipes_data: List[Dict]) -> List[str]:
        """
        Add multiple recipes to the database and Elasticsearch with feature vector generation

        Args:
            recipes_data: List of recipe dicts, each containing:
                - id: str (required) - must be unique
                - title: str (required)
                - description: str (optional)
                - recipe_url: str (optional)
                - image_url: str (optional)
                - ingredients: List[str] (required)
                - instructions: List[str] (required)
                - category: str (optional)
                - cuisine: str (optional)
                - site_name: str (optional)
                - keywords: List[str] (optional)
                - dietary_restrictions: List[str] (optional)
                - total_time: int (optional)
                - overall_rating: float (optional)

        Returns:
            List[str]: List of successfully added recipe IDs
        """
        if not recipes_data:
            return []

        # Prepare recipes for database insertion
        recipes_to_add = []
        for recipe in recipes_data:
            recipe_id = recipe["id"]
            if self.db_manager.recipe_exists(recipe_id):
                logger.warning(f"Recipe with ID {recipe_id} already exists, skipping")
                continue

            db_recipe_data = {
                "id": recipe_id,
                "title": self._safe_string(recipe.get("title", "")).strip(),
                "description": self._safe_string(recipe.get("description", "")).strip(),
                "recipe_url": self._safe_string(recipe.get("recipe_url", "")).strip(),
                "image_url": self._safe_string(recipe.get("image_url", "")).strip(),
                "ingredients": json.dumps(recipe.get("ingredients", [])),
                "instructions": json.dumps(recipe.get("instructions", [])),
                "category": self._safe_string(recipe.get("category", "")).strip(),
                "cuisine": self._safe_string(recipe.get("cuisine", "")).strip(),
                "site_name": self._safe_string(recipe.get("site_name", "")).strip(),
                "keywords": json.dumps(recipe.get("keywords", [])),
                "dietary_restrictions": json.dumps(
                    recipe.get("dietary_restrictions", [])
                ),
                "total_time": self._safe_int(recipe.get("total_time")),
                "overall_rating": self._safe_float(recipe.get("overall_rating")),
            }
            recipes_to_add.append(db_recipe_data)

        if not recipes_to_add:
            return []

        # Batch insert into database
        try:
            recipe_ids = self.db_manager.add_multiple_recipes(recipes_to_add)
            logger.info(f"Successfully added {len(recipe_ids)} recipes to database")
        except Exception as e:
            logger.error(f"Database error while adding recipes: {e}")
            raise RuntimeError(f"Failed to add recipes to database: {e}")

        # Bulk index in Elasticsearch with feature vectors
        if self.es_service:
            # Check if feature vector models are available
            if not self.es_service.tfidf_vectorizer or not self.es_service.pca:
                logger.warning(
                    "Feature vector models not loaded. Recipes will be indexed without feature vectors."
                )
                logger.warning(
                    "This may affect similarity search functionality for new recipes."
                )

            try:
                # Convert database format back to dict format for feature vector generation
                es_recipes_data = []
                for recipe_data in recipes_to_add:
                    es_recipe_data = {
                        "id": recipe_data["id"],
                        "title": recipe_data["title"],
                        "description": recipe_data["description"],
                        "recipe_url": recipe_data["recipe_url"],
                        "image_url": recipe_data["image_url"],
                        "ingredients": json.loads(recipe_data["ingredients"]),
                        "instructions": json.loads(recipe_data["instructions"]),
                        "category": recipe_data["category"],
                        "cuisine": recipe_data["cuisine"],
                        "site_name": recipe_data["site_name"],
                        "keywords": json.loads(recipe_data["keywords"]),
                        "dietary_restrictions": json.loads(
                            recipe_data["dietary_restrictions"]
                        ),
                        "total_time": recipe_data["total_time"],
                        "overall_rating": recipe_data["overall_rating"],
                    }
                    es_recipes_data.append(es_recipe_data)

                # Bulk index all recipes
                indexed_recipe_ids = self.es_service.bulk_index_recipes(es_recipes_data)

                logger.info(
                    f"Successfully bulk indexed {len(indexed_recipe_ids)} recipes in Elasticsearch with feature vectors"
                )

            except Exception as e:
                logger.error(f"Failed to bulk index recipes in Elasticsearch: {e}")

        return recipe_ids

    def get_most_similar_recipe(self, recipe_id: str) -> Optional[Dict]:
        """
        Get the most similar recipe to the given recipe for validation purposes using Elasticsearch.

        Args:
            recipe_id: ID of the recipe to find similar recipes for

        Returns:
            Dictionary with similar recipe information or None if not found
        """
        if not self.es_service:
            logger.warning("Elasticsearch service not available for similarity check")
            return None

        # Create user feedback that treats the current recipe as liked to find similar recipes
        user_feedback = {"liked": [recipe_id], "disliked": []}

        # Use generate_recommendations to find similar recipes, excluding the current recipe
        prev_recommended_ids = [recipe_id]  # Exclude the recipe itself
        similar_recipe_ids = self.es_service.generate_recommendations(
            user_feedback=user_feedback,
            prev_recommended_ids=prev_recommended_ids,
            num_recommendations=1,
        )

        if not similar_recipe_ids:
            logger.warning(f"No similar recipes found for {recipe_id}")
            return None

        # Get the similar recipe details
        similar_recipe_id = similar_recipe_ids[0]
        similar_recipe = self.db_manager.get_recipe(similar_recipe_id)

        if not similar_recipe:
            logger.warning(f"Similar recipe {similar_recipe_id} not found in database")
            return None

        return {
            "similar_recipe": similar_recipe,
            "similar_recipe_title": similar_recipe.title,
        }
