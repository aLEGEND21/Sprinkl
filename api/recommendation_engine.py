# recommendation_engine.py - AI-powered recipe recommendation engine
import json
import logging
from typing import List, Dict, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RecommendationEngine:
    def __init__(self):
        self.vectorizer = None
        self.recipe_features = None
        self.recipe_similarity_matrix = None
        self.recipes_cache = None
        self.cache_expiry = None

    def clean_text(self, text: str) -> str:
        """Clean and normalize text for similarity comparison"""
        if not text:
            return ""
        # Convert to lowercase and remove special characters
        text = re.sub(r"[^a-zA-Z\s]", " ", str(text).lower())
        # Remove extra whitespace
        text = " ".join(text.split())
        return text

    def extract_recipe_features(self, recipe: Dict) -> str:
        """Extract features from a recipe for similarity comparison"""
        features = []

        # Add recipe name
        if recipe.get("recipe_name"):
            features.append(self.clean_text(recipe["recipe_name"]))

        # Add ingredients
        if recipe.get("ingredient_list"):
            try:
                if isinstance(recipe["ingredient_list"], str):
                    ingredients = json.loads(recipe["ingredient_list"])
                else:
                    ingredients = recipe["ingredient_list"]

                if isinstance(ingredients, list):
                    features.extend([self.clean_text(ing) for ing in ingredients])
            except (json.JSONDecodeError, TypeError):
                pass

        # Add cuisine
        if recipe.get("cuisine"):
            features.append(self.clean_text(recipe["cuisine"]))
            # Add cuisine multiple times to increase its weight
            features.append(self.clean_text(recipe["cuisine"]))

        # Add cooking time category
        if recipe.get("time_mins"):
            time_mins = recipe["time_mins"]
            if time_mins <= 30:
                features.append("quick meal")
            elif time_mins <= 60:
                features.append("medium cook time")
            else:
                features.append("long cook time")

        return " ".join(features)

    async def build_similarity_matrix(self, db_manager):
        """Build the recipe similarity matrix"""
        try:
            logger.info("Building recipe similarity matrix...")

            # Get all recipes
            recipes = await db_manager.search_recipes(limit=10000)  # Get all recipes

            if not recipes:
                logger.warning("No recipes found in database")
                return

            # Extract features
            recipe_texts = []
            for recipe in recipes:
                features = self.extract_recipe_features(recipe)
                recipe_texts.append(features)

            # Create TF-IDF vectors
            self.vectorizer = TfidfVectorizer(
                max_features=2000,
                stop_words="english",
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.95,
            )

            tfidf_matrix = self.vectorizer.fit_transform(recipe_texts)

            # Calculate cosine similarity
            self.recipe_similarity_matrix = cosine_similarity(tfidf_matrix)
            self.recipes_cache = recipes
            self.cache_expiry = datetime.now() + timedelta(hours=6)  # Cache for 6 hours

            logger.info(f"Similarity matrix built for {len(recipes)} recipes")

        except Exception as e:
            logger.error(f"Error building similarity matrix: {str(e)}")

    async def get_similar_recipes(
        self, recipe_id: str, db_manager, num_similar: int = 10
    ) -> List[str]:
        """Get similar recipes to a given recipe"""
        try:
            # Check if we need to rebuild cache
            if (
                not self.recipes_cache
                or not self.recipe_similarity_matrix
                or not self.cache_expiry
                or datetime.now() > self.cache_expiry
            ):
                await self.build_similarity_matrix(db_manager)

            if not self.recipes_cache or not self.recipe_similarity_matrix:
                return []

            # Find the recipe index
            recipe_index = None
            for i, recipe in enumerate(self.recipes_cache):
                if recipe["id"] == recipe_id:
                    recipe_index = i
                    break

            if recipe_index is None:
                return []

            # Get similarity scores
            similarity_scores = self.recipe_similarity_matrix[recipe_index]

            # Get top similar recipes (excluding the recipe itself)
            similar_indices = np.argsort(similarity_scores)[::-1][1 : num_similar + 1]

            return [self.recipes_cache[i]["id"] for i in similar_indices]

        except Exception as e:
            logger.error(f"Error getting similar recipes: {str(e)}")
            return []

    async def get_content_based_recommendations(
        self, user_id: str, db_manager, num_recommendations: int = 20
    ) -> List[str]:
        """Generate content-based recommendations based on user's liked recipes"""
        try:
            # Get user feedback
            feedback = await db_manager.get_user_feedback(user_id)
            liked_recipes = feedback.get("liked", [])
            disliked_recipes = feedback.get("disliked", [])

            if not liked_recipes:
                # If no likes, return popular recipes (high ingredient count or certain cuisines)
                recipes = await db_manager.search_recipes(limit=num_recommendations)
                return [recipe["id"] for recipe in recipes]

            # Get similar recipes for each liked recipe
            all_similar_recipes = []
            for liked_recipe_id in liked_recipes[-5:]:  # Consider last 5 liked recipes
                similar_recipes = await self.get_similar_recipes(
                    liked_recipe_id, db_manager, 10
                )
                all_similar_recipes.extend(similar_recipes)

            # Remove duplicates and disliked recipes
            unique_recommendations = []
            seen = set(liked_recipes + disliked_recipes)

            for recipe_id in all_similar_recipes:
                if recipe_id not in seen:
                    unique_recommendations.append(recipe_id)
                    seen.add(recipe_id)

                if len(unique_recommendations) >= num_recommendations:
                    break

            # If we don't have enough recommendations, add some popular ones
            if len(unique_recommendations) < num_recommendations:
                additional_recipes = await db_manager.search_recipes(
                    limit=num_recommendations - len(unique_recommendations)
                )
                for recipe in additional_recipes:
                    if recipe["id"] not in seen:
                        unique_recommendations.append(recipe["id"])
                        if len(unique_recommendations) >= num_recommendations:
                            break

            return unique_recommendations

        except Exception as e:
            logger.error(f"Error generating content-based recommendations: {str(e)}")
            return []

    async def get_cuisine_based_recommendations(
        self, user_id: str, db_manager, num_recommendations: int = 10
    ) -> List[str]:
        """Generate recommendations based on user's preferred cuisines"""
        try:
            # Get user stats to find favorite cuisines
            stats = await db_manager.get_user_stats(user_id)
            favorite_cuisines = stats.get("favorite_cuisines", [])

            if not favorite_cuisines:
                return []

            recommendations = []
            feedback = await db_manager.get_user_feedback(user_id)
            excluded_recipes = set(
                feedback.get("liked", []) + feedback.get("disliked", [])
            )

            # Get recipes from favorite cuisines
            for cuisine_data in favorite_cuisines[:3]:  # Top 3 cuisines
                cuisine = cuisine_data["cuisine"]
                cuisine_recipes = await db_manager.search_recipes(
                    cuisine=cuisine, limit=num_recommendations
                )

                for recipe in cuisine_recipes:
                    if (
                        recipe["id"] not in excluded_recipes
                        and recipe["id"] not in recommendations
                    ):
                        recommendations.append(recipe["id"])
                        if len(recommendations) >= num_recommendations:
                            break

                if len(recommendations) >= num_recommendations:
                    break

            return recommendations

        except Exception as e:
            logger.error(f"Error generating cuisine-based recommendations: {str(e)}")
            return []

    async def generate_fresh_recommendations(
        self, user_id: str, db_manager
    ) -> List[Dict]:
        """Generate fresh recommendations using multiple strategies"""
        try:
            # Generate recommendations using different strategies
            content_recs = await self.get_content_based_recommendations(
                user_id, db_manager, 15
            )
            cuisine_recs = await self.get_cuisine_based_recommendations(
                user_id, db_manager, 10
            )

            # Combine and deduplicate
            all_recommendations = content_recs + cuisine_recs
            unique_recommendations = []
            seen = set()

            for recipe_id in all_recommendations:
                if recipe_id not in seen:
                    unique_recommendations.append(recipe_id)
                    seen.add(recipe_id)
                    if len(unique_recommendations) >= 20:
                        break

            # Save recommendations to database
            await db_manager.save_recommendations(user_id, unique_recommendations)

            # Get full recipe details
            recommendations = []
            for recipe_id in unique_recommendations:
                recipe = await db_manager.get_recipe_by_id(recipe_id)
                if recipe:
                    recommendations.append(recipe)

            return recommendations

        except Exception as e:
            logger.error(f"Error generating fresh recommendations: {str(e)}")
            return []

    async def get_recommendations(
        self,
        user_id: str,
        db_manager,
        num_recommendations: int = 10,
        cuisine_filter: Optional[str] = None,
        max_time_mins: Optional[int] = None,
    ) -> List[Dict]:
        """Get recommendations for a user, using cached if available"""
        try:
            # Try to get saved recommendations first
            saved_recipe_ids = await db_manager.get_saved_recommendations(user_id)

            # If no saved recommendations or they're stale, generate fresh ones
            if not saved_recipe_ids:
                logger.info(
                    f"No saved recommendations for user {user_id}, generating fresh ones"
                )
                return await self.generate_fresh_recommendations(user_id, db_manager)

            # Get full recipe details
            recommendations = []
            for recipe_id in saved_recipe_ids:
                recipe = await db_manager.get_recipe_by_id(recipe_id)
                if recipe:
                    # Apply filters
                    if cuisine_filter and recipe.get("cuisine") != cuisine_filter:
                        continue
                    if (
                        max_time_mins
                        and recipe.get("time_mins")
                        and recipe["time_mins"] > max_time_mins
                    ):
                        continue

                    recommendations.append(recipe)

                    if len(recommendations) >= num_recommendations:
                        break

            # If filters eliminated too many recommendations, generate fresh ones
            if len(recommendations) < num_recommendations // 2:
                return await self.generate_fresh_recommendations(user_id, db_manager)

            return recommendations

        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}")
            return []

    async def update_user_recommendations(self, user_id: str, db_manager):
        """Update recommendations when user provides feedback"""
        try:
            # Generate fresh recommendations
            await self.generate_fresh_recommendations(user_id, db_manager)
            logger.info(f"Updated recommendations for user {user_id}")

        except Exception as e:
            logger.error(f"Error updating user recommendations: {str(e)}")
