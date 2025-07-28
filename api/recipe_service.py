# recipe_service.py - Service for adding new recipes with feature vector calculation
import json
import logging
import os
from typing import Dict, List, Optional

import joblib
import numpy as np
from database import DatabaseManager
from dotenv import load_dotenv
from es_service import ElasticsearchService
from models import Recipe

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# ML Models directory
ML_MODELS_DIR = "ml_models"  # Path within the container


class RecipeService:
    def __init__(
        self,
        db_manager: DatabaseManager,
        es_service: ElasticsearchService,
        rec_engine=None,
    ):
        """Initialize the RecipeService with loaded ML models, database manager, elasticsearch service, and recommendation engine"""
        self.title_vectorizer = None
        self.ingredients_vectorizer = None
        self.instructions_vectorizer = None
        self.description_vectorizer = None
        self.cuisine_encoder = None
        self.db_manager = db_manager
        self.es_service = es_service
        self.rec_engine = rec_engine

        self._load_ml_models()

    def _load_ml_models(self):
        """Load the pre-trained ML models from the ml_models directory"""
        try:
            self.title_vectorizer = joblib.load(
                os.path.join(ML_MODELS_DIR, "title_vectorizer.joblib")
            )
            self.ingredients_vectorizer = joblib.load(
                os.path.join(ML_MODELS_DIR, "ingredients_vectorizer.joblib")
            )
            self.instructions_vectorizer = joblib.load(
                os.path.join(ML_MODELS_DIR, "instructions_vectorizer.joblib")
            )
            self.description_vectorizer = joblib.load(
                os.path.join(ML_MODELS_DIR, "description_vectorizer.joblib")
            )
            self.cuisine_encoder = joblib.load(
                os.path.join(ML_MODELS_DIR, "cuisine_encoder.joblib")
            )

            logger.info("Successfully loaded all ML models")
        except Exception as e:
            logger.error(f"Failed to load ML models: {e}")
            raise RuntimeError(
                f"ML models not found. Please run the initialization script first: {e}"
            )

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

    def _calculate_feature_vector(self, recipe_data: Dict) -> List[float]:
        """Calculate feature vector for a recipe using the loaded ML models"""
        try:
            # Transform text features
            title_vec = self.title_vectorizer.transform(
                [self._safe_string(recipe_data.get("title", "")).strip()]
            ).toarray()

            ingredients_vec = self.ingredients_vectorizer.transform(
                [" ".join(recipe_data.get("ingredients", [])).strip()]
            ).toarray()

            instructions_vec = self.instructions_vectorizer.transform(
                [" ".join(recipe_data.get("instructions", [])).strip()]
            ).toarray()

            description_vec = self.description_vectorizer.transform(
                [self._safe_string(recipe_data.get("description", "")).strip()]
            ).toarray()

            # Transform categorical features
            cuisine_vec = self.cuisine_encoder.transform(
                np.array(
                    [self._safe_string(recipe_data.get("cuisine", "")).strip()]
                ).reshape(-1, 1)
            )

            # Concatenate all vectors to form the final feature vector
            combined_feature_vector = np.concatenate(
                [
                    title_vec.flatten(),
                    ingredients_vec.flatten(),
                    instructions_vec.flatten(),
                    description_vec.flatten(),
                    cuisine_vec.flatten(),
                ]
            ).tolist()

            return combined_feature_vector

        except Exception as e:
            logger.error(f"Error calculating feature vector: {e}")
            raise RuntimeError(f"Failed to calculate feature vector: {e}")

    def add_recipe(self, recipes_data: List[Dict]) -> List[str]:
        """
        Add multiple recipes to the database and Elasticsearch efficiently

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

        # Pre-calculate feature vectors for all recipes
        recipes_with_vectors = []
        for recipe in recipes_data:
            recipe_id = recipe["id"]
            if self.db_manager.recipe_exists(recipe_id):
                logger.warning(f"Recipe with ID {recipe_id} already exists, skipping")
                continue

            feature_vector = self._calculate_feature_vector(recipe)
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
                "feature_vector": json.dumps(feature_vector),
            }
            recipes_with_vectors.append(db_recipe_data)

        if not recipes_with_vectors:
            return []

        # Batch insert into database
        try:
            recipe_ids = self.db_manager.add_multiple_recipes(recipes_with_vectors)
        except Exception as e:
            logger.error(f"Database error while adding recipes: {e}")
            raise RuntimeError(f"Failed to add recipes to database: {e}")

        # Batch index in Elasticsearch
        if self.es_service:
            try:
                for recipe_data in recipes_with_vectors:
                    success = self.es_service.index_recipe(
                        recipe_data["id"], recipe_data["title"]
                    )
                    if not success:
                        logger.warning(
                            f"Failed to index recipe in Elasticsearch: {recipe_data['id']}"
                        )
            except Exception as e:
                logger.warning(f"Failed to index recipes in Elasticsearch: {e}")

        # Refresh recommendation engine once for all new recipes
        if self.rec_engine:
            try:
                self.rec_engine.refresh_models()
                logger.info("Recommendation engine refreshed with new recipes")
            except Exception as e:
                logger.warning(f"Failed to refresh recommendation engine: {e}")

        return recipe_ids

    def get_most_similar_recipe(self, recipe_id: str) -> Optional[Dict]:
        """
        Get the most similar recipe to the given recipe for validation purposes.

        Args:
            recipe_id: ID of the recipe to find similar recipes for

        Returns:
            Dictionary with similar recipe information or None if not found
        """
        if not self.rec_engine:
            logger.warning("Recommendation engine not available for similarity check")
            return None

        try:
            similar_id, similarity_score, similar_title = (
                self.rec_engine.find_most_similar_recipe(recipe_id)
            )

            if similar_id is None:
                return None

            # Get the similar recipe details
            similar_recipe = self.db_manager.get_recipe(similar_id)

            return {
                "similar_recipe": similar_recipe,
                "similarity_score": similarity_score,
                "similar_recipe_title": similar_title,
            }

        except Exception as e:
            logger.error(f"Error finding similar recipe: {e}")
            return None

    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """Get a recipe by ID using DatabaseManager"""
        try:
            return self.db_manager.get_recipe(recipe_id)
        except Exception as e:
            logger.error(f"Error getting recipe {recipe_id}: {e}")
            return None
