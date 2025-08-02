# init.py - Add the recipes from the .json file to the database and configure Elasticsearch
# MariaDB doesn't run this script automatically when the container is started, unlike init.sql
# Instead, we have a separate container called init that runs this script when it is built, and the other containers
# wait for it to finish before starting.

import json
import os
import pickle
import sys
import time
from typing import Any, Dict, List, Tuple

import numpy as np
import pymysql
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler

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

# PCA configuration
MAX_DIMENSIONS = 4000


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


def prepare_recipe_text(recipe: Dict[str, Any]) -> str:
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


def generate_feature_vectors(
    recipes: List[Dict[str, Any]],
) -> Tuple[np.ndarray, TfidfVectorizer, PCA]:
    """Generate TF-IDF feature vectors and apply PCA dimensionality reduction"""
    print("Generating feature vectors...")

    # Prepare text data for all recipes
    recipe_texts = []
    valid_recipe_indices = []

    for i, recipe in enumerate(recipes):
        text = prepare_recipe_text(recipe)
        if text.strip():  # Only include non-empty texts
            recipe_texts.append(text)
            valid_recipe_indices.append(i)

    print(f"Prepared {len(recipe_texts)} recipe texts for vectorization")

    # Create TF-IDF vectorizer with bag of words approach
    tfidf_vectorizer = TfidfVectorizer(
        max_features=10000,  # Limit features to prevent memory issues
        stop_words="english",
        ngram_range=(1, 2),  # Include unigrams and bigrams
        min_df=2,  # Minimum document frequency
        max_df=0.95,  # Maximum document frequency
        lowercase=True,
        strip_accents="unicode",
    )

    # Fit and transform the text data
    tfidf_matrix = tfidf_vectorizer.fit_transform(recipe_texts)
    print(f"TF-IDF matrix shape: {tfidf_matrix.shape}")

    # Convert to dense array for PCA
    tfidf_dense = tfidf_matrix.toarray()

    # Apply PCA for dimensionality reduction
    n_components = min(MAX_DIMENSIONS, tfidf_dense.shape[1], tfidf_dense.shape[0])

    # Standardize the data before PCA
    scaler = StandardScaler()
    tfidf_scaled = scaler.fit_transform(tfidf_dense)

    # Apply PCA
    pca = PCA(n_components=n_components, random_state=42)
    feature_vectors = pca.fit_transform(tfidf_scaled)

    print(
        f"PCA reduced dimensions from {tfidf_dense.shape[1]} to {feature_vectors.shape[1]}"
    )
    print(f"Explained variance ratio: {pca.explained_variance_ratio_.sum():.4f}")

    return feature_vectors, tfidf_vectorizer, pca, valid_recipe_indices


def save_models(
    tfidf_vectorizer: TfidfVectorizer,
    pca: PCA,
    filename: str = "ml_models/recipe_models.pkl",
):
    """Save the trained TF-IDF vectorizer and PCA model for later use"""
    try:
        models = {"tfidf_vectorizer": tfidf_vectorizer, "pca": pca}
        with open(filename, "wb") as f:
            pickle.dump(models, f)
        print(f"Models saved to {filename}")
        return True
    except Exception as e:
        print(f"Error saving models: {e}")
        return False


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

    # --- Generate Feature Vectors ---
    print("\nStarting feature vector generation...")
    start_time = time.time()

    feature_vectors, tfidf_vectorizer, pca, valid_recipe_indices = (
        generate_feature_vectors(all_recipes_raw_data)
    )

    vectorization_time = time.time() - start_time
    print(f"Feature vector generation completed in {vectorization_time:.2f} seconds")

    # Save the trained models
    save_models(tfidf_vectorizer, pca)

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
            # Define the mapping for recipe search with feature vectors
            feature_vector_dims = feature_vectors.shape[1]
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
                            "dims": feature_vector_dims,
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

            es.indices.create(index=ES_INDEX, body=mapping)
            print(f"Created Elasticsearch index: {ES_INDEX}")
        else:
            print(f"Elasticsearch index {ES_INDEX} already exists")

        # Index recipes in Elasticsearch with feature vectors
        indexed_count = 0
        for i, recipe in enumerate(all_recipes_raw_data):
            try:
                # Get feature vector for this recipe
                if i in valid_recipe_indices:
                    vector_index = valid_recipe_indices.index(i)
                    feature_vector = feature_vectors[vector_index]
                else:
                    # If no feature vector (empty text), use zero vector
                    feature_vector = np.zeros(feature_vectors.shape[1])

                # Create document for Elasticsearch
                doc = {
                    "id": recipe["id"],
                    "title": safe_string(recipe.get("title", "")).strip(),
                    "description": safe_string(recipe.get("description", "")).strip(),
                    "recipe_url": safe_string(recipe.get("recipe_url", "")).strip(),
                    "image_url": safe_string(recipe.get("image_url", "")).strip(),
                    "ingredients": recipe.get("ingredients", []),
                    "instructions": recipe.get("instructions", []),
                    "category": safe_string(recipe.get("category", "")).strip(),
                    "cuisine": safe_string(recipe.get("cuisine", "")).strip(),
                    "site_name": safe_string(recipe.get("site_name", "")).strip(),
                    "keywords": recipe.get("keywords", []),
                    "dietary_restrictions": recipe.get("dietary_restrictions", []),
                    "total_time": safe_int(recipe.get("total_time")),
                    "overall_rating": safe_float(recipe.get("overall_rating")),
                    "feature_vector": feature_vector.tolist(),
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

        # Test feature vector similarity functionality
        print("\nTesting feature vector similarity functionality...")

        # Recipe IDs for various alcoholic beverages to use as reference
        test_recipe_ids = [
            "9de17a77-ac3b-44ee-9867-3653fbe398b1",
            "dad7e78b-f2db-43fc-8e2a-b590ec3ed79b",
            "ed536e65-8e1e-4585-ab9e-9325cc03cce0",
        ]

        # Find feature vectors for test recipes
        test_feature_vectors = []
        exclude_ids = []

        for recipe_id in test_recipe_ids:
            try:
                # Search for the recipe by ID
                search_result = es.search(
                    index=ES_INDEX,
                    body={"query": {"term": {"id": recipe_id}}, "size": 1},
                )

                if search_result["hits"]["total"]["value"] > 0:
                    recipe_doc = search_result["hits"]["hits"][0]["_source"]
                    feature_vector = np.array(recipe_doc.get("feature_vector", []))

                    if len(feature_vector) > 0:
                        test_feature_vectors.append(feature_vector)
                        exclude_ids.append(recipe_id)
                        print(f"Found feature vector for test recipe: {recipe_id}")
                    else:
                        print(f"No feature vector found for test recipe: {recipe_id}")
                else:
                    print(f"Test recipe not found in index: {recipe_id}")

            except Exception as e:
                print(f"Error finding feature vector for {recipe_id}: {e}")

        if test_feature_vectors:
            # Create user preference vector by averaging test recipe vectors
            user_preference = np.mean(test_feature_vectors, axis=0)

            # Normalize the preference vector
            norm = np.linalg.norm(user_preference)
            if norm > 0:
                user_preference = user_preference / norm

            print(
                f"Created user preference vector with {len(user_preference)} dimensions"
            )

            # Find similar recipes using cosine similarity
            try:
                search_result = es.search(
                    index=ES_INDEX,
                    body={
                        "query": {
                            "script_score": {
                                "query": {
                                    "bool": {
                                        "must_not": [{"terms": {"id": exclude_ids}}]
                                    },
                                },
                                "script": {
                                    "source": "cosineSimilarity(params.query_vector, 'feature_vector') + 1.0",
                                    "params": {
                                        "query_vector": user_preference.tolist()
                                    },
                                },
                            }
                        },
                        "size": 10,
                    },
                )

                print(
                    f"Feature vector similarity query returned {len(search_result['hits']['hits'])} results"
                )
                if search_result["hits"]["hits"]:
                    print("Top similar recipes:")
                    # Get the maximum score for normalization
                    max_score = search_result["hits"]["hits"][0]["_score"]

                    for i, hit in enumerate(search_result["hits"]["hits"][:10], 1):
                        source = hit["_source"]
                        # Normalize score to 0-1 range
                        normalized_score = (
                            hit["_score"] / max_score if max_score > 0 else 0
                        )
                        print(
                            f"  {i}. {source['title']} (Score: {hit['_score']:.2f}, Normalized: {normalized_score:.3f})"
                        )
                        print(f"     Category: {source.get('category', 'N/A')}")
                        print(f"     Cuisine: {source.get('cuisine', 'N/A')}")
                else:
                    print("No similar recipes found")

            except Exception as e:
                print(f"Error testing feature vector similarity query: {e}")
        else:
            print("No valid feature vectors found for test recipes")

    except Exception as e:
        print(f"Elasticsearch error: {e}")
        print("Make sure Elasticsearch is running and accessible")
