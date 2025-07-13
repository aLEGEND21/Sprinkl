import json
import logging
import random
import warnings
from typing import Dict, List

import numpy as np
from database import DatabaseManager
from sklearn.metrics.pairwise import cosine_similarity

# Suppress scikit-learn numerical warnings
warnings.filterwarnings(
    "ignore", category=RuntimeWarning, module="sklearn.utils.extmath"
)
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")


logger = logging.getLogger(__name__)


class RecommendationEngine:
    def __init__(self, db: DatabaseManager):
        self.id_vec_map = db.get_all_feature_vectors()
        self.id_title_map = (
            db.get_all_recipe_titles()
        )  # Used for logging/debug purposes
        self.recipe_ids = []
        self.feature_matrix = None

        # Extract feature vectors and recipe IDs
        feature_vectors = []
        for recipe_id, feature_vector_json in self.id_vec_map.items():
            try:
                # Parse the JSON feature vector
                feature_vector = json.loads(feature_vector_json)

                # Ensure feature_vector is a list of numbers
                if isinstance(feature_vector, list):
                    feature_vectors.append(feature_vector)
                    self.recipe_ids.append(recipe_id)
                else:
                    logger.warning(
                        f"Feature vector for recipe {recipe_id} ({self.id_title_map[recipe_id]}) is not a list"
                    )

            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(
                    f"Error parsing feature vector for recipe {recipe_id} ({self.id_title_map[recipe_id]}): {e}"
                )
                continue

        # Convert to numpy array for efficient computation
        if feature_vectors:
            self.feature_matrix = np.array(feature_vectors)
            logger.info(
                f"Feature matrix created with shape: {self.feature_matrix.shape}"
            )
            logger.info(f"Number of recipes processed: {len(self.recipe_ids)}")
        else:
            logger.error("No valid feature vectors found")
            self.feature_matrix = None

    def generate_recommendations(
        self,
        user_feedback: Dict[str, List[str]],
        prev_recommended_ids: List[str],
        num_recommendations: int = 10,
        like_weight: float = 1.0,
        dislike_weight: float = -0.5,
    ) -> List[str]:
        """
        Get personalized recommendations based on user's feedback. Returns random recipes if user has
        no feedback. Excluded recipes are recipes that have already been recommended or shown.

        Args:
            user_feedback: Dict of recipe IDs the user has liked or disliked
            excluded_recipe_ids: List of recipe IDs to exclude from recommendations
            num_recommendations: Number of recommendations to return
            like_weight: Weight for liked recipes (positive)
            dislike_weight: Weight for disliked recipes (negative)

        Returns:
            List of tuples (recipe_id, similarity_score) sorted by similarity
        """

        liked_recipe_ids = user_feedback["liked"]
        disliked_recipe_ids = user_feedback["disliked"]

        if self.feature_matrix is None:
            logger.error("Feature matrix not available")
            return []

        # If user has no feedback, return 10 random recipes
        if not liked_recipe_ids and not disliked_recipe_ids:
            logger.info(
                f"User has no feedback, returning {num_recommendations} random recipes"
            )
            random_recipes = random.sample(
                self.recipe_ids, min(num_recommendations, len(self.recipe_ids))
            )
            return random_recipes

        logger.info(
            f"Generating recommendations for user with {len(liked_recipe_ids)} likes and {len(disliked_recipe_ids)} dislikes"
        )

        # Get indices of user's feedback recipes in our matrices
        liked_indices = []
        disliked_indices = []

        for recipe_id in liked_recipe_ids:
            if recipe_id in self.recipe_ids:
                liked_indices.append(self.recipe_ids.index(recipe_id))
            else:
                logger.warning(
                    f"Liked recipe {recipe_id} ({self.id_title_map[recipe_id]}) not found in TF-IDF matrix"
                )

        for recipe_id in disliked_recipe_ids:
            if recipe_id in self.recipe_ids:
                disliked_indices.append(self.recipe_ids.index(recipe_id))
            else:
                logger.warning(
                    f"Disliked recipe {recipe_id} ({self.id_title_map[recipe_id]}) not found in TF-IDF matrix"
                )

        # Extract feature vectors for user's feedback
        liked_vectors = None
        disliked_vectors = None

        if liked_indices:
            liked_vectors = self.feature_matrix[liked_indices]

        if disliked_indices:
            disliked_vectors = self.feature_matrix[disliked_indices]

        # Create user preference vector
        preference_vector = None

        if liked_vectors is not None and len(liked_vectors) > 0:
            liked_avg = np.mean(liked_vectors, axis=0)
            preference_vector = like_weight * liked_avg

        if disliked_vectors is not None and len(disliked_vectors) > 0:
            disliked_avg = np.mean(disliked_vectors, axis=0)
            if preference_vector is not None:
                preference_vector += dislike_weight * disliked_avg
            else:
                preference_vector = dislike_weight * disliked_avg

        if preference_vector is None:
            logger.error("Could not create preference vector")
            return []

        # Compute similarities with all recipes
        similarities = cosine_similarity([preference_vector], self.feature_matrix)[0]

        # Create list of (recipe_id, similarity_score) tuples
        recipe_similarities = []
        excluded_recipe_ids = set(
            prev_recommended_ids + liked_recipe_ids + disliked_recipe_ids
        )
        for i, similarity_score in enumerate(similarities):
            recipe_id = self.recipe_ids[i]

            # Skip recipes the user has already seen or been recommended but not shown
            if recipe_id in excluded_recipe_ids:
                continue

            recipe_similarities.append((recipe_id, similarity_score))

        # Sort by similarity score (descending) and return top recommendations
        recipe_similarities.sort(key=lambda x: x[1], reverse=True)
        top_recommendations = recipe_similarities[:num_recommendations]

        logger.info(f"Generated {len(top_recommendations)} recommendations")
        if top_recommendations:
            rec_id, rec_sim = top_recommendations[0]
            rec_title = self.id_title_map[rec_id]
            logger.info(
                f"Top recommendation: {rec_title} ({rec_id}) with similarity {rec_sim:.4f}"
            )

        return [r_id for r_id, _ in top_recommendations]
