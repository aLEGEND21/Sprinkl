# es_service.py - Elasticsearch service for recipe search functionality
import logging
import pickle
import random
from typing import Dict, List, Optional

import numpy as np
from database import DatabaseManager
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ElasticsearchService:
    ES_HOST = "elasticsearch"
    ES_PORT = 9200
    INDEX_NAME = "recipes"

    def __init__(self, db_manager: DatabaseManager):
        """Initialize Elasticsearch connection and wait for readiness"""
        self.es = Elasticsearch(f"http://{self.ES_HOST}:{self.ES_PORT}")
        self.db_manager = db_manager
        self.tfidf_vectorizer = None
        self.pca = None
        self._load_models()

    def _load_models(self):
        """Load the trained TF-IDF vectorizer and PCA model"""
        try:
            with open("ml_models/recipe_models.pkl", "rb") as f:
                models = pickle.load(f)
                self.tfidf_vectorizer = models["tfidf_vectorizer"]
                self.pca = models["pca"]
            logger.info("Successfully loaded TF-IDF and PCA models")
        except Exception as e:
            logger.warning(
                f"Could not load models: {e}. Feature vector generation will not be available."
            )

    def _prepare_recipe_text(self, recipe: Dict) -> str:
        """Prepare text content from recipe for TF-IDF vectorization"""
        text_parts = []

        # Title
        if recipe.get("title"):
            text_parts.append(recipe["title"])

        # Description
        if recipe.get("description"):
            text_parts.append(recipe["description"])

        # Ingredients (join list into string)
        if recipe.get("ingredients"):
            ingredients_text = " ".join(recipe["ingredients"])
            text_parts.append(ingredients_text)

        # Instructions (join list into string)
        if recipe.get("instructions"):
            instructions_text = " ".join(recipe["instructions"])
            text_parts.append(instructions_text)

        # Keywords
        if recipe.get("keywords"):
            keywords_text = " ".join(recipe["keywords"])
            text_parts.append(keywords_text)

        # Category and cuisine
        if recipe.get("category"):
            text_parts.append(recipe["category"])

        if recipe.get("cuisine"):
            text_parts.append(recipe["cuisine"])

        # Dietary restrictions
        if recipe.get("dietary_restrictions"):
            dietary_text = " ".join(recipe["dietary_restrictions"])
            text_parts.append(dietary_text)

        return " ".join(text_parts)

    def _generate_feature_vector(self, recipe: Dict) -> Optional[np.ndarray]:
        """Generate feature vector for a single recipe"""
        if not self.tfidf_vectorizer or not self.pca:
            logger.warning("Models not loaded, cannot generate feature vector")
            return None

        try:
            # Prepare text for the recipe
            text = self._prepare_recipe_text(recipe)
            if not text.strip():
                logger.warning("Recipe has no text content for vectorization")
                return None

            # Transform text using TF-IDF
            tfidf_vector = self.tfidf_vectorizer.transform([text])

            # Convert to dense array and apply PCA
            tfidf_dense = tfidf_vector.toarray()
            feature_vector = self.pca.transform(tfidf_dense)[0]

            return feature_vector

        except Exception as e:
            logger.error(f"Error generating feature vector: {e}")
            return None

    def index_recipe(
        self, recipe_id: str, title: str, recipe_data: Dict = None
    ) -> bool:
        """
        Index a recipe in Elasticsearch for search functionality with feature vector

        Args:
            recipe_id: Unique identifier for the recipe
            title: Recipe title for search indexing
            recipe_data: Full recipe data for feature vector generation

        Returns:
            bool: True if indexing was successful, False otherwise
        """
        try:
            # Create document for Elasticsearch
            doc = {
                "id": recipe_id,
                "title": title,
            }

            # Add feature vector if recipe data is provided and models are loaded
            if recipe_data and self.tfidf_vectorizer and self.pca:
                feature_vector = self._generate_feature_vector(recipe_data)
                if feature_vector is not None:
                    doc["feature_vector"] = feature_vector.tolist()
                    logger.info(f"Added feature vector to recipe {recipe_id}")

            # Index the document
            self.es.index(index=self.INDEX_NAME, body=doc)

            # Refresh the index to make document searchable immediately
            self.es.indices.refresh(index=self.INDEX_NAME)

            logger.info(
                f"Successfully indexed recipe in Elasticsearch with ID: {recipe_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to index recipe in Elasticsearch: {e}")
            return False

    def create_index_if_not_exists(self) -> bool:
        """
        Create the recipes index if it doesn't exist with feature vector support

        Returns:
            bool: True if index exists or was created successfully, False otherwise
        """
        try:
            # Check if index exists
            if not self.es.indices.exists(index=self.INDEX_NAME):
                # Define the mapping for recipe search with feature vectors
                mapping = {
                    "mappings": {
                        "properties": {
                            "id": {"type": "keyword"},
                            "title": {
                                "type": "text",
                                "analyzer": "standard",
                                "fields": {
                                    "keyword": {"type": "keyword"},
                                },
                            },
                            "description": {
                                "type": "text",
                                "analyzer": "standard",
                            },
                            "recipe_url": {"type": "keyword"},
                            "image_url": {"type": "keyword"},
                            "ingredients": {
                                "type": "text",
                                "analyzer": "standard",
                            },
                            "instructions": {
                                "type": "text",
                                "analyzer": "standard",
                            },
                            "category": {
                                "type": "text",
                                "analyzer": "standard",
                                "fields": {"keyword": {"type": "keyword"}},
                            },
                            "cuisine": {
                                "type": "text",
                                "analyzer": "standard",
                                "fields": {"keyword": {"type": "keyword"}},
                            },
                            "site_name": {
                                "type": "text",
                                "analyzer": "standard",
                                "fields": {"keyword": {"type": "keyword"}},
                            },
                            "keywords": {
                                "type": "text",
                                "analyzer": "standard",
                            },
                            "dietary_restrictions": {
                                "type": "text",
                                "analyzer": "standard",
                                "fields": {"keyword": {"type": "keyword"}},
                            },
                            "total_time": {"type": "integer"},
                            "overall_rating": {"type": "float"},
                            "feature_vector": {
                                "type": "dense_vector",
                                "dims": 4000,  # Default dimension, will be updated if models are loaded
                                "index": True,
                                "similarity": "cosine",
                            },
                        }
                    },
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                    },
                }

                # Update feature vector dimensions if models are loaded
                if self.pca:
                    mapping["mappings"]["properties"]["feature_vector"]["dims"] = (
                        self.pca.n_components_
                    )

                self.es.indices.create(index=self.INDEX_NAME, body=mapping)
                logger.info(f"Created Elasticsearch index: {self.INDEX_NAME}")
            else:
                logger.info(f"Elasticsearch index {self.INDEX_NAME} already exists")

            return True

        except Exception as e:
            logger.error(f"Error creating Elasticsearch index: {e}")
            return False

    def _get_recipe_feature_vectors(
        self, recipe_ids: List[str]
    ) -> Dict[str, np.ndarray]:
        """Get feature vectors for given recipe IDs from Elasticsearch"""
        feature_vectors = {}

        for recipe_id in recipe_ids:
            try:
                # Search for the recipe by ID
                search_result = self.es.search(
                    index=self.INDEX_NAME,
                    body={"query": {"term": {"id": recipe_id}}, "size": 1},
                )

                if search_result["hits"]["total"]["value"] > 0:
                    recipe_doc = search_result["hits"]["hits"][0]["_source"]
                    feature_vector = np.array(recipe_doc.get("feature_vector", []))

                    if len(feature_vector) > 0:
                        feature_vectors[recipe_id] = feature_vector
                        logger.debug(f"Found feature vector for recipe: {recipe_id}")
                    else:
                        logger.warning(
                            f"No feature vector found for recipe: {recipe_id}"
                        )
                else:
                    logger.warning(f"Recipe not found in index: {recipe_id}")

            except Exception as e:
                logger.error(f"Error finding feature vector for {recipe_id}: {e}")

        logger.info(
            f"Found feature vectors for {len(feature_vectors)} out of {len(recipe_ids)} recipes"
        )
        return feature_vectors

    def _create_user_preference_vector(
        self,
        liked_feature_vectors: Dict[str, np.ndarray],
        disliked_feature_vectors: Dict[str, np.ndarray] = None,
        like_weight: float = 1.0,
        dislike_weight: float = -0.5,
    ) -> Optional[np.ndarray]:
        """
        Create user preference vector by combining liked and disliked feature vectors

        Args:
            liked_feature_vectors: Feature vectors of liked recipes
            disliked_feature_vectors: Feature vectors of disliked recipes (optional)
            like_weight: Weight for liked recipes (positive)
            dislike_weight: Weight for disliked recipes (negative)

        Returns:
            User preference vector that incorporates both likes and dislikes
        """
        if not liked_feature_vectors and not disliked_feature_vectors:
            logger.error("No feature vectors provided for user preference calculation")
            return None

        try:
            # Initialize preference vector
            if liked_feature_vectors:
                # Get the dimension from the first liked vector
                first_vector = next(iter(liked_feature_vectors.values()))
                user_preference = np.zeros_like(first_vector)
            elif disliked_feature_vectors:
                # Get the dimension from the first disliked vector
                first_vector = next(iter(disliked_feature_vectors.values()))
                user_preference = np.zeros_like(first_vector)
            else:
                return None

            # Add weighted contribution from liked recipes
            if liked_feature_vectors:
                liked_vectors = list(liked_feature_vectors.values())
                liked_mean = np.mean(liked_vectors, axis=0)
                user_preference += like_weight * liked_mean
                logger.info(
                    f"Added {len(liked_feature_vectors)} liked recipes with weight {like_weight}"
                )

            # Add weighted contribution from disliked recipes (negative weight pushes away from disliked features)
            if disliked_feature_vectors:
                disliked_vectors = list(disliked_feature_vectors.values())
                disliked_mean = np.mean(disliked_vectors, axis=0)
                user_preference += dislike_weight * disliked_mean
                logger.info(
                    f"Added {len(disliked_feature_vectors)} disliked recipes with weight {dislike_weight}"
                )

            # Normalize the preference vector
            norm = np.linalg.norm(user_preference)
            if norm > 0:
                user_preference = user_preference / norm

            logger.info(
                f"Created user preference vector with {len(user_preference)} dimensions"
            )
            return user_preference

        except Exception as e:
            logger.error(f"Error creating user preference vector: {e}")
            return None

    def generate_recommendations(
        self,
        user_feedback: Dict[str, List[str]],
        prev_recommended_ids: List[str],
        num_recommendations: int = 10,
        like_weight: float = 1.0,
        dislike_weight: float = -0.5,
    ) -> List[str]:
        """
        Get personalized recommendations based on user's feedback using feature vector similarity.
        Uses precomputed feature vectors stored in Elasticsearch. Incorporates both liked and disliked recipes
        to create a comprehensive user preference vector. Returns random recipes if user has no feedback.

        Args:
            user_feedback: Dict with "liked" and "disliked" lists of recipe IDs
            prev_recommended_ids: List of recipe IDs to exclude from recommendations
            num_recommendations: Number of recommendations to return
            like_weight: Weight for liked recipes (positive, attracts similar recipes)
            dislike_weight: Weight for disliked recipes (negative, pushes away from similar recipes)

        Returns:
            List of recipe IDs sorted by similarity score
        """
        liked_recipe_ids = user_feedback.get("liked", [])
        disliked_recipe_ids = user_feedback.get("disliked", [])

        # If user has no feedback, return random recipes
        if not liked_recipe_ids and not disliked_recipe_ids:
            logger.info(
                f"User has no feedback, returning {num_recommendations} random recipes"
            )
            return self._get_random_recipes(num_recommendations)

        logger.info(
            f"Generating recommendations for user with {len(liked_recipe_ids)} likes and {len(disliked_recipe_ids)} dislikes"
        )

        # Get feature vectors for liked recipes
        liked_feature_vectors = self._get_recipe_feature_vectors(liked_recipe_ids)

        # Get feature vectors for disliked recipes
        disliked_feature_vectors = self._get_recipe_feature_vectors(disliked_recipe_ids)

        # Check if we have any feature vectors to work with
        if not liked_feature_vectors and not disliked_feature_vectors:
            logger.warning(
                "No feature vectors found for any recipes, falling back to random recipes"
            )
            return self._get_random_recipes(num_recommendations)

        # Create user preference vector incorporating both likes and dislikes
        user_preference = self._create_user_preference_vector(
            liked_feature_vectors, disliked_feature_vectors, like_weight, dislike_weight
        )

        if user_preference is None:
            logger.warning(
                "Failed to create user preference vector, falling back to random recipes"
            )
            return self._get_random_recipes(num_recommendations)

        # Build exclusion list
        exclude_ids = []
        if liked_feature_vectors:
            exclude_ids.extend(list(liked_feature_vectors.keys()))
        if disliked_feature_vectors:
            exclude_ids.extend(list(disliked_feature_vectors.keys()))
        exclude_ids.extend(
            disliked_recipe_ids
        )  # Include any disliked recipes that didn't have feature vectors
        exclude_ids.extend(prev_recommended_ids)

        # Log what we're using for recommendations
        if liked_feature_vectors and disliked_feature_vectors:
            logger.info(
                f"Using {len(liked_feature_vectors)} liked and {len(disliked_feature_vectors)} disliked recipes for similarity search"
            )
        elif liked_feature_vectors:
            logger.info(
                f"Using {len(liked_feature_vectors)} liked recipes for similarity search"
            )
        elif disliked_feature_vectors:
            logger.info(
                f"Using {len(disliked_feature_vectors)} disliked recipes for similarity search (avoiding similar recipes)"
            )

        logger.info(f"Excluding {len(exclude_ids)} recipes")

        # Find similar recipes using cosine similarity
        try:
            search_result = self.es.search(
                index=self.INDEX_NAME,
                body={
                    "query": {
                        "script_score": {
                            "query": {
                                "bool": {"must_not": [{"terms": {"id": exclude_ids}}]},
                            },
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'feature_vector') + 1.0",
                                "params": {"query_vector": user_preference.tolist()},
                            },
                        }
                    },
                    "size": num_recommendations
                    * 2,  # Get more candidates for filtering
                    "_source": [
                        "id",
                        "title",
                        "description",
                        "recipe_url",
                        "image_url",
                        "ingredients",
                        "instructions",
                        "category",
                        "cuisine",
                        "site_name",
                        "keywords",
                        "dietary_restrictions",
                        "total_time",
                        "overall_rating",
                    ],
                },
            )

            # Extract results
            hits = search_result["hits"]["hits"]
            total_hits = search_result["hits"]["total"]["value"]

            logger.info(
                f"Feature vector similarity search returned {len(hits)} hits out of {total_hits} total documents"
            )

            if not hits:
                logger.warning(
                    "No results from feature vector similarity search, falling back to random recipes"
                )
                return self._get_random_recipes(num_recommendations)

            # Extract recipe IDs and scores
            recipe_data = []
            for hit in hits:
                recipe_id = hit["_source"]["id"]
                score = hit["_score"]
                recipe_data.append((recipe_id, score))

            # Sort by score (highest first)
            recipe_data.sort(key=lambda x: x[1], reverse=True)

            # Log the recommendations with normalized scores
            max_score = recipe_data[0][1] if recipe_data else 1.0
            logger.info(f"Generated {len(recipe_data)} recommendations:")
            for i, (recipe_id, score) in enumerate(recipe_data[:num_recommendations]):
                normalized_score = score / max_score if max_score > 0 else 0
                recipe = (
                    self.db_manager.get_recipe(recipe_id) if self.db_manager else None
                )
                title = recipe.title if recipe else "Unknown"
                logger.info(
                    f"  {i + 1}. {title} (ID: {recipe_id}, Score: {score:.2f}, Normalized: {normalized_score:.3f})"
                )

            # Return the top recommendations
            recipe_ids = [
                recipe_id for recipe_id, _ in recipe_data[:num_recommendations]
            ]

            return recipe_ids

        except Exception as e:
            logger.error(f"Error executing feature vector similarity search: {e}")
            logger.info("Falling back to random recipes")
            return self._get_random_recipes(num_recommendations)

    def _get_random_recipes(self, num_recommendations: int) -> List[str]:
        """Helper method to get random recipes as fallback"""
        try:
            response = self.es.search(
                index=self.INDEX_NAME,
                body={
                    "query": {"match_all": {}},
                    "size": 1000,
                    "_source": ["id"],
                },
            )

            all_recipe_ids = [hit["_source"]["id"] for hit in response["hits"]["hits"]]

            if not all_recipe_ids:
                logger.warning("No recipes found in Elasticsearch")
                return []

            return random.sample(
                all_recipe_ids, min(num_recommendations, len(all_recipe_ids))
            )
        except Exception as e:
            logger.error(f"Error getting random recipes: {e}")
            return []

    def search_recipes(
        self, query: str, page: int = 1, size: int = 10, fuzziness: str = "AUTO"
    ) -> Dict:
        """
        Search recipes by title using fuzzy search with pagination

        Args:
            query: Search query string
            page: Page number (1-based)
            size: Number of results per page
            fuzziness: Fuzzy search level ("AUTO", "0", "1", "2")

        Returns:
            Dictionary containing search results and pagination info
        """
        try:
            # Calculate from parameter for pagination
            from_value = (page - 1) * size

            # Build search query with multiple strategies
            search_body = {
                "query": {
                    "bool": {
                        "should": [
                            # Exact match (highest priority)
                            {"match": {"title": {"query": query, "boost": 3}}},
                            # Prefix match for partial words
                            {"prefix": {"title": {"value": query, "boost": 2}}},
                            # Fuzzy match for typos
                            {
                                "fuzzy": {
                                    "title": {
                                        "value": query,
                                        "fuzziness": fuzziness,
                                        "max_expansions": 100,
                                        "prefix_length": 1,
                                        "transpositions": True,
                                    }
                                }
                            },
                            # Contains match
                            {
                                "wildcard": {
                                    "title": {"value": f"*{query}*", "boost": 1}
                                }
                            },
                        ],
                        "minimum_should_match": 1,
                    }
                },
                "from": from_value,
                "size": size,
                "sort": [{"_score": {"order": "desc"}}],
            }

            # Execute search
            response = self.es.search(index=self.INDEX_NAME, body=search_body)

            # Extract results
            hits = response["hits"]["hits"]
            total_hits = response["hits"]["total"]["value"]

            # Get recipe IDs from search results
            recipe_ids = [hit["_source"]["id"] for hit in hits]

            # Calculate pagination info
            total_pages = (total_hits + size - 1) // size
            has_next = page < total_pages
            has_previous = page > 1

            return {
                "recipe_ids": recipe_ids,
                "total_hits": total_hits,
                "page": page,
                "size": size,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous,
                "search_scores": [hit["_score"] for hit in hits],
            }

        except Exception as e:
            logger.error(f"Error searching Elasticsearch: {str(e)}")
            return None
