# elasticsearch_service.py - Elasticsearch service for recipe search functionality
import logging
import os
from typing import Dict

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ElasticsearchService:
    def __init__(self):
        """Initialize Elasticsearch connection"""
        self.es_host = os.getenv("ES_HOST", "elasticsearch")
        self.es_port = int(os.getenv("ES_PORT", "9200"))
        self.index_name = "recipes"

        # Initialize Elasticsearch client
        self.es = Elasticsearch(f"http://{self.es_host}:{self.es_port}")

        # Test connection
        if not self.es.ping():
            logger.error("Cannot connect to Elasticsearch")
            raise ConnectionError("Cannot connect to Elasticsearch")

        logger.info(f"Connected to Elasticsearch at {self.es_host}:{self.es_port}")

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

            # Build search query with fuzzy matching
            search_body = {
                "query": {
                    "fuzzy": {
                        "title": {
                            "value": query,
                            "fuzziness": fuzziness,
                            "max_expansions": 50,
                            "prefix_length": 0,
                            "transpositions": True,
                        }
                    }
                },
                "from": from_value,
                "size": size,
                "sort": [{"_score": {"order": "desc"}}],
            }

            # Execute search
            response = self.es.search(index=self.index_name, body=search_body)

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
