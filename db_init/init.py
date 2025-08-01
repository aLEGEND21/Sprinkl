# init.py - Add the recipes from the .json file to the database and configure Elasticsearch
# This file is not automatically run when the container is started, unlike init.sql
# Instead, run this script manually after the container is started from the db_init directory

import json
import os
import sys

import pymysql
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

# --- Configuration ---
# Load the database information from .env
load_dotenv()
DB_NAME = os.getenv("MARIADB_DATABASE")
DB_USER = os.getenv("MARIADB_USER")
DB_PASSWORD = os.getenv("MARIADB_PASSWORD")
DB_HOST = "mariadb"
DB_PORT = 3306

# Elasticsearch configuration
ES_HOST = "elasticsearch"
ES_PORT = 9200
ES_INDEX = "recipes"

# Path to your JSON file
JSON_FILE_PATH = "init_dataset.json"


# --- Helper Functions ---
def safe_int(value):
    """Safely convert value to int, return None if conversion fails"""
    try:
        return int(float(value)) if value and value != "" else None
    except (ValueError, TypeError):
        return None


def safe_float(value):
    """Safely convert value to float, return None if conversion fails"""
    try:
        return float(value) if value and value != "" else None
    except (ValueError, TypeError):
        return None


def safe_string(value):
    """Safely convert value to string, return empty string if None"""
    return str(value) if value is not None else ""


# --- Main Script ---
if __name__ == "__main__":
    # --- Check if recipes table is empty ---
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4",
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM recipes")
        count = cursor.fetchone()[0]
        if count > 0:
            print(
                f"Recipes table already contains {count} rows. Skipping initialization."
            )
            sys.exit(0)
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking recipes table: {e}")
        sys.exit(1)

    # Read all recipes from JSON file
    print(f"Reading JSON file: {JSON_FILE_PATH}...")
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as jsonfile:
            recipes_data = json.load(jsonfile)
            # Convert the dictionary to a list of recipes with their URLs as keys
            all_recipes_raw_data = []
            for url, recipe in recipes_data.items():
                # The recipe is already formatted for database insertion
                all_recipes_raw_data.append(recipe)
        print(f"Finished reading {len(all_recipes_raw_data)} recipes from JSON.")
    except FileNotFoundError:
        print(f"Error: JSON file not found at {JSON_FILE_PATH}")
        exit()
    except Exception as e:
        print(f"Error reading JSON: {e}")
        exit()

    # --- Connect to DB and Insert Data ---
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4",
        )
        cursor = conn.cursor()
        print(f"Connected to MariaDB database: {DB_NAME}")

        inserted_count = 0
        for recipe in all_recipes_raw_data:
            try:
                # Use the pre-generated UUID from the formatted recipe
                recipe_id = recipe["id"]

                # Check if recipe already exists
                cursor.execute(
                    "SELECT COUNT(*) FROM recipes WHERE id = %s", (recipe_id,)
                )
                count = cursor.fetchone()[0]
                if count > 0:
                    print(
                        f"Recipe with ID {recipe_id} already exists, skipping: {recipe.get('title', 'Unknown')}"
                    )
                    continue

                # Insert the data into the database
                cursor.execute(
                    """
                    INSERT INTO recipes (
                        id, title, description, recipe_url, image_url, ingredients, instructions,
                        category, cuisine, site_name, keywords, dietary_restrictions,
                        total_time, overall_rating
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        recipe["id"],
                        recipe["title"],
                        recipe["description"],
                        recipe["recipe_url"],
                        recipe["image_url"],
                        json.dumps(recipe["ingredients"]),  # Serialize list to JSON
                        json.dumps(recipe["instructions"]),  # Serialize list to JSON
                        recipe["category"],
                        recipe["cuisine"],
                        recipe["site_name"],
                        json.dumps(recipe["keywords"]),  # Serialize list to JSON
                        json.dumps(
                            recipe["dietary_restrictions"]
                        ),  # Serialize list to JSON
                        recipe["total_time"],
                        recipe["overall_rating"],
                    ),
                )

                inserted_count += 1
                if inserted_count % 100 == 0:
                    print(f"Inserted {inserted_count} recipes...")

            except Exception as e:
                print(f"Error inserting recipe (ID: {recipe.get('id', 'N/A')}): {e}")
                print(f"Recipe data causing error: {recipe}")
                continue

        # Commit the changes
        conn.commit()
        print(f"Successfully inserted {inserted_count} recipes into the database!")

    except pymysql.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("Database connection closed.")

    # --- Elasticsearch Indexing ---
    print("\nStarting Elasticsearch indexing...")

    try:
        # Connect to Elasticsearch
        es = Elasticsearch(f"http://{ES_HOST}:{ES_PORT}")

        # Check if Elasticsearch is running
        if not es.ping():
            print("Error: Cannot connect to Elasticsearch. Make sure it's running.")
            exit(1)

        print(f"Connected to Elasticsearch at {ES_HOST}:{ES_PORT}")

        # Create index if it doesn't exist
        if not es.indices.exists(index=ES_INDEX):
            # Define the mapping for recipe search and more_like_this queries
            mapping = {
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "title": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"},
                                "ngram": {"type": "text", "analyzer": "ngram_analyzer"},
                            },
                        },
                        "description": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "ngram": {"type": "text", "analyzer": "ngram_analyzer"}
                            },
                        },
                        "recipe_url": {"type": "keyword"},
                        "image_url": {"type": "keyword"},
                        "ingredients": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"},
                                "ngram": {"type": "text", "analyzer": "ngram_analyzer"},
                            },
                        },
                        "instructions": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "ngram": {"type": "text", "analyzer": "ngram_analyzer"}
                            },
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
                            "fields": {
                                "keyword": {"type": "keyword"},
                                "ngram": {"type": "text", "analyzer": "ngram_analyzer"},
                            },
                        },
                        "dietary_restrictions": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {"keyword": {"type": "keyword"}},
                        },
                        "total_time": {"type": "integer"},
                        "overall_rating": {"type": "float"},
                    }
                },
                "settings": {
                    "analysis": {
                        "analyzer": {
                            "ngram_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "ngram_filter"],
                            }
                        },
                        "filter": {
                            "ngram_filter": {
                                "type": "ngram",
                                "min_gram": 2,
                                "max_gram": 3,
                            }
                        },
                    },
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                },
            }

            es.indices.create(index=ES_INDEX, body=mapping)
            print(f"Created Elasticsearch index: {ES_INDEX}")
        else:
            print(f"Elasticsearch index {ES_INDEX} already exists")

        # Index recipes in Elasticsearch
        indexed_count = 0
        for recipe in all_recipes_raw_data:
            try:
                # Create document for Elasticsearch
                doc = {
                    "id": recipe["id"],
                    "title": safe_string(recipe.get("title", "")).strip(),
                    "description": safe_string(recipe.get("description", "")).strip(),
                    "recipe_url": safe_string(recipe.get("recipe_url", "")).strip(),
                    "image_url": safe_string(recipe.get("image_url", "")).strip(),
                    "ingredients": recipe.get(
                        "ingredients", []
                    ),  # Keep as array for better MLT
                    "instructions": recipe.get(
                        "instructions", []
                    ),  # Keep as array for better MLT
                    "category": safe_string(recipe.get("category", "")).strip(),
                    "cuisine": safe_string(recipe.get("cuisine", "")).strip(),
                    "site_name": safe_string(recipe.get("site_name", "")).strip(),
                    "keywords": recipe.get(
                        "keywords", []
                    ),  # Keep as array for better MLT
                    "dietary_restrictions": recipe.get(
                        "dietary_restrictions", []
                    ),  # Keep as array for better MLT
                    "total_time": safe_int(recipe.get("total_time")),
                    "overall_rating": safe_float(recipe.get("overall_rating")),
                }

                # Index the document using the recipe ID as the document ID
                es.index(index=ES_INDEX, id=recipe["id"], body=doc)
                indexed_count += 1

                if indexed_count % 100 == 0:
                    print(f"Indexed {indexed_count} recipes in Elasticsearch...")

            except Exception as e:
                print(f"Error indexing recipe in Elasticsearch: {e}")
                continue

        # Refresh the index to make documents searchable immediately
        es.indices.refresh(index=ES_INDEX)
        print(f"Successfully indexed {indexed_count} recipes in Elasticsearch!")

        # Test search functionality
        print("\nTesting Elasticsearch search functionality...")
        query = "apple"
        test_response = es.search(
            index=ES_INDEX, body={"query": {"match": {"title": query}}, "size": 5}
        )

        print(
            f"Test search for '{query}' returned {len(test_response['hits']['hits'])} results"
        )
        if test_response["hits"]["hits"]:
            print("First 5 results:")
            for hit in test_response["hits"]["hits"][:5]:
                print(f"  - {hit['_source']['title']}")

        # Test more_like_this functionality
        print("\nTesting more_like_this functionality...")

        # Recipe IDs for various alcoholic beverages to use as reference
        test_recipe_ids = [
            "9de17a77-ac3b-44ee-9867-3653fbe398b1",
            "dad7e78b-f2db-43fc-8e2a-b590ec3ed79b",
            "ed536e65-8e1e-4585-ab9e-9325cc03cce0",
        ]

        # Create like clauses for the more_like_this query
        like_clauses = []
        exclude_ids = []

        for recipe_id in test_recipe_ids:
            like_clauses.append({"_index": ES_INDEX, "_id": recipe_id})
            exclude_ids.append(recipe_id)

        # Create the single more_like_this query with all test recipes
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
            "size": 10,
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
            more_like_response = es.search(index=ES_INDEX, body=query)

            print(
                f"more_like_this query returned {len(more_like_response['hits']['hits'])} results"
            )
            if more_like_response["hits"]["hits"]:
                print("Top similar recipes:")
                # Get the maximum score for normalization
                max_score = more_like_response["hits"]["hits"][0]["_score"]

                for i, hit in enumerate(more_like_response["hits"]["hits"][:10], 1):
                    source = hit["_source"]
                    # Normalize score to 0-1 range
                    normalized_score = hit["_score"] / max_score if max_score > 0 else 0
                    print(
                        f"  {i}. {source['title']} (Score: {hit['_score']:.2f}, Normalized: {normalized_score:.3f})"
                    )
                    print(f"     Category: {source.get('category', 'N/A')}")
                    print(f"     Cuisine: {source.get('cuisine', 'N/A')}")
            else:
                print("No similar recipes found")

        except Exception as e:
            print(f"Error testing more_like_this query: {e}")

    except Exception as e:
        print(f"Elasticsearch error: {e}")
        print("Make sure Elasticsearch is running and accessible")
