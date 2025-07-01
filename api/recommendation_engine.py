#!/usr/bin/env python3
"""
Memory-Efficient Recommendation Engine using Database-Driven Similarity

This module implements a memory-efficient recommendation engine that:
- Loads recipes on-demand from the database
- Computes similarities directly from stored feature vectors
- Minimizes memory usage by not storing large datasets in memory
- Uses efficient database queries for similarity computations
"""

import json
import logging
import os
import random
import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pymysql
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

# Suppress scikit-learn numerical warnings
warnings.filterwarnings(
    "ignore", category=RuntimeWarning, module="sklearn.utils.extmath"
)
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class RecommendationEngine:
    def __init__(self):
        self.db_config = {
            "host": os.getenv("MARIADB_HOST", "localhost"),
            "port": int(os.getenv("MARIADB_PORT", "3306")),
            "user": os.getenv("MARIADB_USER", "root"),
            "password": os.getenv("MARIADB_PASSWORD"),
            "database": os.getenv("MARIADB_DATABASE", "foodapp_db"),
            "charset": "utf8mb4",
        }

        # Cache for frequently accessed data (minimal memory usage)
        self._recipe_count = None
        self._recipe_ids_cache = set()

        logger.info("Memory-efficient recommendation engine initialized!")

    def _get_connection(self):
        """Get a database connection"""
        return pymysql.connect(**self.db_config)

    def _get_recipe_count(self) -> int:
        """Get total number of recipes with feature vectors"""
        if self._recipe_count is None:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT COUNT(*) FROM recipes WHERE feature_vector IS NOT NULL"
                )
                self._recipe_count = cursor.fetchone()[0]
            finally:
                cursor.close()
                conn.close()
        return self._recipe_count

    def _get_recipe_ids(self) -> set:
        """Get set of all recipe IDs with feature vectors"""
        if not self._recipe_ids_cache:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT id FROM recipes WHERE feature_vector IS NOT NULL"
                )
                self._recipe_ids_cache = {row[0] for row in cursor.fetchall()}
            except Exception as e:
                logger.error(f"_get_recipe_ids: error loading recipe IDs: {e}")
                self._recipe_ids_cache = set()
            finally:
                cursor.close()
                conn.close()
        return self._recipe_ids_cache

    def _get_recipe_feature_vector(self, recipe_id: str) -> Optional[np.ndarray]:
        """Get feature vector for a specific recipe"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT feature_vector FROM recipes WHERE id = %s", (recipe_id,)
            )
            result = cursor.fetchone()
            if result and result[0]:
                feature_vector = json.loads(result[0])
                vector_array = np.array(feature_vector, dtype=np.float64)

                # Check for invalid values
                if np.any(np.isnan(vector_array)) or np.any(np.isinf(vector_array)):
                    logger.warning(
                        f"Invalid feature vector for recipe {recipe_id}: contains NaN or Inf values"
                    )
                    return None

                # Check if vector is all zeros
                if np.all(vector_array == 0):
                    logger.warning(f"Zero feature vector for recipe {recipe_id}")
                    return None

                # Normalize with safety check
                norm = np.linalg.norm(vector_array)
                if norm > 0:
                    return vector_array / norm
                else:
                    logger.warning(f"Zero norm feature vector for recipe {recipe_id}")
                    return None
            return None
        except Exception as e:
            logger.error(f"Error getting feature vector for recipe {recipe_id}: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    def _get_multiple_feature_vectors(
        self, recipe_ids: List[str]
    ) -> Dict[str, np.ndarray]:
        """Get feature vectors for multiple recipes efficiently"""
        if not recipe_ids:
            return {}

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Create placeholders for the IN clause
            placeholders = ",".join(["%s"] * len(recipe_ids))
            cursor.execute(
                f"SELECT id, feature_vector FROM recipes WHERE id IN ({placeholders})",
                tuple(
                    recipe_ids
                ),  # Convert list to tuple for proper parameter expansion
            )

            vectors = {}
            for row in cursor.fetchall():
                recipe_id, feature_vector_json = row
                if feature_vector_json:
                    try:
                        feature_vector = json.loads(feature_vector_json)
                        vector_array = np.array(feature_vector, dtype=np.float64)

                        # Check for invalid values
                        if np.any(np.isnan(vector_array)) or np.any(
                            np.isinf(vector_array)
                        ):
                            logger.warning(
                                f"Invalid feature vector for recipe {recipe_id}: contains NaN or Inf values"
                            )
                            continue

                        # Check if vector is all zeros
                        if np.all(vector_array == 0):
                            logger.warning(
                                f"Zero feature vector for recipe {recipe_id}"
                            )
                            continue

                        # Normalize with safety check
                        norm = np.linalg.norm(vector_array)
                        if norm > 0:
                            vectors[recipe_id] = vector_array / norm
                        else:
                            logger.warning(
                                f"Zero norm feature vector for recipe {recipe_id}"
                            )
                            continue

                    except json.JSONDecodeError:
                        logger.warning(
                            f"Invalid JSON in feature vector for recipe {recipe_id}"
                        )
                        continue
                    except Exception as e:
                        logger.error(
                            f"Error processing feature vector for recipe {recipe_id}: {e}"
                        )
                        continue

            return vectors
        except Exception as e:
            logger.error(f"Error getting feature vectors: {e}")
            return {}
        finally:
            cursor.close()
            conn.close()

    def _compute_similarity_batch(
        self,
        target_vector: np.ndarray,
        recipe_ids: List[str],
        exclude_recipe_ids: Optional[List[str]] = None,
    ) -> List[Tuple[str, float]]:
        """Compute similarity between target vector and a batch of recipes"""
        if not recipe_ids:
            return []

        # Get feature vectors for the batch
        feature_vectors = self._get_multiple_feature_vectors(recipe_ids)
        if not feature_vectors:
            return []

        # Validate target vector
        if (
            target_vector is None
            or np.any(np.isnan(target_vector))
            or np.any(np.isinf(target_vector))
        ):
            logger.warning("Invalid target vector for similarity computation")
            return []

        # Convert to arrays for computation
        vectors_array = np.array(list(feature_vectors.values()))
        recipe_id_list = list(feature_vectors.keys())

        # Additional validation for vectors array
        if np.any(np.isnan(vectors_array)) or np.any(np.isinf(vectors_array)):
            logger.warning("Invalid vectors in batch for similarity computation")
            return []

        try:
            # Compute similarities with error handling
            similarities = cosine_similarity([target_vector], vectors_array)[0]

            # Check for invalid similarity scores
            valid_similarities = []
            for i, sim in enumerate(similarities):
                if not np.isnan(sim) and not np.isinf(sim):
                    valid_similarities.append((recipe_id_list[i], float(sim)))
                else:
                    logger.warning(
                        f"Invalid similarity score for recipe {recipe_id_list[i]}: {sim}"
                    )

            # Create results with exclusions
            results = []
            exclude_set = set(exclude_recipe_ids or [])

            for recipe_id, similarity in valid_similarities:
                if recipe_id not in exclude_set:
                    results.append((recipe_id, similarity))

            return results

        except Exception as e:
            logger.error(f"Error computing similarities: {e}")
            return []

    def get_random_recipes(
        self, num_recipes: int = 5, exclude_recipe_ids: Optional[List[str]] = None
    ) -> List[str]:
        """Get random recipes efficiently"""
        all_recipe_ids = self._get_recipe_ids()
        exclude_set = set(exclude_recipe_ids or [])

        # Filter out excluded recipes
        available_ids = list(all_recipe_ids - exclude_set)

        if len(available_ids) <= num_recipes:
            return available_ids

        return random.sample(available_ids, num_recipes)

    def compute_user_preference_vector(
        self,
        liked_recipes: List[str],
        disliked_recipes: List[str],
        like_weight: float = 1.0,
        dislike_weight: float = -0.5,
    ) -> Optional[np.ndarray]:
        """Compute user preference vector from liked/disliked recipes"""
        if not liked_recipes and not disliked_recipes:
            return None

        # Get feature vectors for all user feedback recipes
        all_feedback_ids = liked_recipes + disliked_recipes
        feature_vectors = self._get_multiple_feature_vectors(all_feedback_ids)

        if not feature_vectors:
            return None

        # Compute weighted preference vector
        preference_vector = None

        for recipe_id in liked_recipes:
            if recipe_id in feature_vectors:
                vector = feature_vectors[recipe_id]
                # Validate vector before using
                if (
                    vector is not None
                    and not np.any(np.isnan(vector))
                    and not np.any(np.isinf(vector))
                ):
                    if preference_vector is None:
                        preference_vector = like_weight * vector
                    else:
                        preference_vector += like_weight * vector

        for recipe_id in disliked_recipes:
            if recipe_id in feature_vectors:
                vector = feature_vectors[recipe_id]
                # Validate vector before using
                if (
                    vector is not None
                    and not np.any(np.isnan(vector))
                    and not np.any(np.isinf(vector))
                ):
                    if preference_vector is None:
                        preference_vector = dislike_weight * vector
                    else:
                        preference_vector += dislike_weight * vector

        # Normalize if we have a preference vector
        if preference_vector is not None:
            # Check for invalid values
            if np.any(np.isnan(preference_vector)) or np.any(
                np.isinf(preference_vector)
            ):
                logger.warning("Invalid preference vector computed")
                return None

            norm = np.linalg.norm(preference_vector)
            if norm > 0:
                preference_vector = preference_vector / norm
            else:
                logger.warning("Zero norm preference vector computed")
                return None

        return preference_vector

    def find_similar_recipes(
        self,
        preference_vector: np.ndarray,
        num_recipes: int = 20,
        exclude_recipe_ids: Optional[List[str]] = None,
        batch_size: int = 1000,
    ) -> List[Tuple[str, float, Dict]]:
        """Find recipes similar to preference vector using batched computation"""
        if preference_vector is None:
            return []

        all_recipe_ids = list(self._get_recipe_ids())
        exclude_set = set(exclude_recipe_ids or [])

        # Filter out excluded recipes
        available_ids = [rid for rid in all_recipe_ids if rid not in exclude_set]

        if not available_ids:
            return []

        # Process in batches to manage memory
        all_similarities = []

        for i in range(0, len(available_ids), batch_size):
            batch_ids = available_ids[i : i + batch_size]
            batch_similarities = self._compute_similarity_batch(
                preference_vector, batch_ids, exclude_recipe_ids
            )
            all_similarities.extend(batch_similarities)

        # Sort by similarity and get top results
        all_similarities.sort(key=lambda x: x[1], reverse=True)
        top_similarities = all_similarities[:num_recipes]

        # Get recipe data for top results
        top_recipe_ids = [recipe_id for recipe_id, _ in top_similarities]
        recipe_data = self._get_recipe_data(top_recipe_ids)

        # Combine results
        results = []
        for recipe_id, similarity_score in top_similarities:
            recipe_info = recipe_data.get(recipe_id, {})
            results.append((recipe_id, similarity_score, recipe_info))

        return results

    def _get_recipe_data(self, recipe_ids: List[str]) -> Dict[str, Dict]:
        """Get basic recipe data for given IDs"""
        if not recipe_ids:
            return {}

        conn = self._get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        try:
            placeholders = ",".join(["%s"] * len(recipe_ids))
            cursor.execute(
                f"""
                SELECT id, title, description, recipe_url, image_url, ingredients, instructions,
                       category, cuisine, site_name, keywords, dietary_restrictions,
                       total_time, overall_rating
                FROM recipes 
                WHERE id IN ({placeholders})
                """,
                tuple(
                    recipe_ids
                ),  # Convert list to tuple for proper parameter expansion
            )

            recipes = {}
            for row in cursor.fetchall():
                # Parse JSON fields
                if row["ingredients"]:
                    try:
                        row["ingredients"] = json.loads(row["ingredients"])
                    except json.JSONDecodeError:
                        row["ingredients"] = []

                if row["instructions"]:
                    try:
                        row["instructions"] = json.loads(row["instructions"])
                    except json.JSONDecodeError:
                        row["instructions"] = []

                if row["keywords"]:
                    try:
                        row["keywords"] = json.loads(row["keywords"])
                    except json.JSONDecodeError:
                        row["keywords"] = []

                if row["dietary_restrictions"]:
                    try:
                        row["dietary_restrictions"] = json.loads(
                            row["dietary_restrictions"]
                        )
                    except json.JSONDecodeError:
                        row["dietary_restrictions"] = []

                recipes[row["id"]] = row

            return recipes
        except Exception as e:
            logger.error(f"Error getting recipe data: {e}")
            return {}
        finally:
            cursor.close()
            conn.close()

    async def get_recommendations(
        self, user_id: str, db_manager, num_recommendations: int = 20
    ) -> List[str]:
        """Generate recommendations using memory-efficient approach"""
        try:
            # Get user feedback
            feedback = await db_manager.get_user_feedback(user_id)
            liked_recipes = feedback.get("liked", [])
            disliked_recipes = feedback.get("disliked", [])
            seen_recipes = liked_recipes + disliked_recipes

            # If user has no feedback, return random recipes
            if not liked_recipes and not disliked_recipes:
                logger.info(
                    f"User {user_id} has no feedback, returning 10 random recipes"
                )
                return self.get_random_recipes(
                    num_recipes=10, exclude_recipe_ids=seen_recipes
                )

            # Compute user preference vector
            logger.info(
                f"User {user_id} has {len(liked_recipes)} likes and {len(disliked_recipes)} dislikes"
            )
            logger.info("Computing user preference vector...")

            user_preference_vector = self.compute_user_preference_vector(
                liked_recipes=liked_recipes,
                disliked_recipes=disliked_recipes,
                like_weight=1.0,
                dislike_weight=-0.5,
            )

            if user_preference_vector is None:
                logger.error("Failed to compute user preference vector")
                return self.get_random_recipes(
                    num_recipes=num_recommendations, exclude_recipe_ids=seen_recipes
                )

            # Find similar recipes
            logger.info("Finding recipes similar to user preference vector...")
            similar_recipes = self.find_similar_recipes(
                preference_vector=user_preference_vector,
                num_recipes=num_recommendations,
                exclude_recipe_ids=seen_recipes,
            )

            # Extract recipe IDs
            recommended_recipe_ids = [
                recipe_id for recipe_id, _, _ in similar_recipes[:num_recommendations]
            ]

            logger.info(
                f"Generated {len(recommended_recipe_ids)} recommendations for user {user_id}"
            )
            return recommended_recipe_ids

        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []
            return []
