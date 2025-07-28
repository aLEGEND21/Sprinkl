# es_service.py - Elasticsearch service for recipe search functionality
import logging
from typing import Dict

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ElasticsearchService:
    ES_HOST = "elasticsearch"
    ES_PORT = 9200
    INDEX_NAME = "recipes"

    def __init__(self):
        """Initialize Elasticsearch connection and wait for readiness"""
        self.es = Elasticsearch(f"http://{self.ES_HOST}:{self.ES_PORT}")

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
