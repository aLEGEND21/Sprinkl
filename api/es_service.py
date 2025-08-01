# es_service.py - Elasticsearch service for recipe search functionality
import logging
import random
from typing import Dict, List

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

    def index_recipe(self, recipe_id: str, title: str) -> bool:
        """
        Index a recipe in Elasticsearch for search functionality

        Args:
            recipe_id: Unique identifier for the recipe
            title: Recipe title for search indexing

        Returns:
            bool: True if indexing was successful, False otherwise
        """
        try:
            # Create document for Elasticsearch
            doc = {
                "id": recipe_id,
                "title": title,
            }

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
        Create the recipes index if it doesn't exist

        Returns:
            bool: True if index exists or was created successfully, False otherwise
        """
        try:
            # Check if index exists
            if not self.es.indices.exists(index=self.INDEX_NAME):
                # Define the mapping for recipe titles
                mapping = {
                    "mappings": {
                        "properties": {
                            "id": {"type": "keyword"},
                            "title": {
                                "type": "text",
                                "analyzer": "standard",
                                "search_analyzer": "standard",
                            },
                        }
                    }
                }

                self.es.indices.create(index=self.INDEX_NAME, body=mapping)
                logger.info(f"Created Elasticsearch index: {self.INDEX_NAME}")
            else:
                logger.info(f"Elasticsearch index {self.INDEX_NAME} already exists")

            return True

        except Exception as e:
            logger.error(f"Error creating Elasticsearch index: {e}")
            return False

    def generate_recommendations(
        self,
        user_feedback: Dict[str, List[str]],
        prev_recommended_ids: List[str],
        num_recommendations: int = 10,
        like_weight: float = 1.0,
        dislike_weight: float = -0.5,
    ) -> List[str]:
        """
        Get personalized recommendations based on user's feedback using Elasticsearch more_like_this.
        Returns random recipes if user has no feedback.

        Args:
            user_feedback: Dict with "liked" and "disliked" lists of recipe IDs
            prev_recommended_ids: List of recipe IDs to exclude from recommendations
            num_recommendations: Number of recommendations to return
            like_weight: Weight for liked recipes (positive)
            dislike_weight: Weight for disliked recipes (negative)

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
            # Get random recipes from Elasticsearch
            response = self.es.search(
                index=self.INDEX_NAME,
                body={
                    "query": {"match_all": {}},
                    "size": 1000,  # Get a reasonable sample
                    "_source": ["id"],
                },
            )

            all_recipe_ids = [hit["_source"]["id"] for hit in response["hits"]["hits"]]

            if not all_recipe_ids:
                logger.warning("No recipes found in Elasticsearch")
                return []

            # Return random sample
            return random.sample(
                all_recipe_ids, min(num_recommendations, len(all_recipe_ids))
            )

        logger.info(
            f"Generating recommendations for user with {len(liked_recipe_ids)} likes and {len(disliked_recipe_ids)} dislikes"
        )

        # Create like clauses for liked recipes
        like_clauses = []
        exclude_ids = []

        # Add liked recipes to like clauses
        for recipe_id in liked_recipe_ids:
            like_clauses.append({"_index": self.INDEX_NAME, "_id": recipe_id})
            exclude_ids.append(recipe_id)

        # Add disliked recipes to exclusions (ignoring them for now)
        for recipe_id in disliked_recipe_ids:
            exclude_ids.append(recipe_id)

        # Add previously recommended recipes to exclusions
        exclude_ids.extend(prev_recommended_ids)

        logger.info(f"Using {len(like_clauses)} liked recipes for more_like_this query")
        logger.info(f"Excluding {len(exclude_ids)} recipes")

        # Create the more_like_this query
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "more_like_this": {
                                "fields": [
                                    "title^2",  # Recipe title (weighted 2x)
                                    "ingredients",  # Recipe ingredients
                                    "keywords",  # Recipe keywords
                                    "category",  # Recipe category
                                    "cuisine",  # Cuisine type
                                ],
                                "like": like_clauses,
                                "min_term_freq": 1,
                                "max_query_terms": 12,
                                "min_doc_freq": 1,
                            }
                        }
                    ],
                    "must_not": [{"terms": {"id": exclude_ids}}],
                }
            },
            "size": num_recommendations * 2,  # Get more candidates for filtering
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
        }

        try:
            # Execute the search
            response = self.es.search(index=self.INDEX_NAME, body=query)

            # Extract results
            hits = response["hits"]["hits"]
            total_hits = response["hits"]["total"]["value"]

            logger.info(
                f"more_like_this search returned {len(hits)} hits out of {total_hits} total documents"
            )

            if not hits:
                logger.warning(
                    "No results from more_like_this search, falling back to random recipes"
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
            logger.error(f"Error executing more_like_this search: {e}")
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
