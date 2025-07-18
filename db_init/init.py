# init.py - Add the recipes from the .json file to the database and configure Elasticsearch
# This file is not automatically run when the container is started, unlike init.sql
# Instead, run this script manually after the container is started from the db_init directory

import json
import os
import uuid

import joblib  # To save/load scikit-learn models
import numpy as np
import pymysql
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder

# --- Configuration ---
# Load the database information from .env
load_dotenv()
DB_NAME = os.getenv("MARIADB_DATABASE")
DB_USER = os.getenv("MARIADB_USER")
DB_PASSWORD = os.getenv("MARIADB_PASSWORD")
DB_HOST = os.getenv("MARIADB_HOST", "localhost")
DB_PORT = int(os.getenv("MARIADB_PORT", "3306"))

# Elasticsearch configuration
ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = int(os.getenv("ES_PORT", "9200"))
ES_INDEX = "recipes"

# Path to your JSON file
JSON_FILE_PATH = "init_dataset.json"

# Directory to save fitted ML models (vectorizers, encoders)
ML_MODELS_DIR = (
    "../ml_models"  # Store in project root since the API will use these models
)
os.makedirs(ML_MODELS_DIR, exist_ok=True)  # Create directory if it doesn't exist


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
    all_recipes_raw_data = []  # To store all data for fitting vectorizers/encoders

    # First pass: Read all data to fit the vectorizers/encoders
    print(f"Reading JSON file: {JSON_FILE_PATH} for ML model training...")
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as jsonfile:
            recipes_data = json.load(jsonfile)
            # Convert the dictionary to a list of recipes with their URLs as keys
            for url, recipe in recipes_data.items():
                recipe["recipe_url"] = url  # Add the URL to the recipe data
                all_recipes_raw_data.append(recipe)
        print(f"Finished reading {len(all_recipes_raw_data)} recipes from JSON.")
    except FileNotFoundError:
        print(f"Error: JSON file not found at {JSON_FILE_PATH}")
        exit()
    except Exception as e:
        print(f"Error reading JSON for ML model training: {e}")
        exit()

    # Prepare data for TF-IDF and One-Hot Encoding
    recipe_titles = [
        safe_string(row.get("title", "")).strip() for row in all_recipes_raw_data
    ]
    ingredients_text = [
        " ".join(row.get("ingredients", [])).strip() for row in all_recipes_raw_data
    ]
    instructions_text = [
        " ".join(row.get("instructions_list", [])).strip()
        for row in all_recipes_raw_data
    ]
    cuisines = [
        safe_string(row.get("cuisine", "")).strip() for row in all_recipes_raw_data
    ]
    descriptions = [
        safe_string(row.get("description", "")).strip() for row in all_recipes_raw_data
    ]

    # --- Initialize and Fit ML Models ---
    print("Fitting TF-IDF Vectorizers and One-Hot Encoders...")

    # TF-IDF for Recipe Title
    title_vectorizer = TfidfVectorizer(
        stop_words="english", max_features=1000
    )  # Limit features to avoid very high dimensionality
    title_vectorizer.fit(recipe_titles)
    joblib.dump(
        title_vectorizer, os.path.join(ML_MODELS_DIR, "title_vectorizer.joblib")
    )

    # TF-IDF for Ingredients
    ingredients_vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
    ingredients_vectorizer.fit(ingredients_text)
    joblib.dump(
        ingredients_vectorizer,
        os.path.join(ML_MODELS_DIR, "ingredients_vectorizer.joblib"),
    )

    # TF-IDF for Instructions
    instructions_vectorizer = TfidfVectorizer(stop_words="english", max_features=3000)
    instructions_vectorizer.fit(instructions_text)
    joblib.dump(
        instructions_vectorizer,
        os.path.join(ML_MODELS_DIR, "instructions_vectorizer.joblib"),
    )

    # TF-IDF for Description
    description_vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
    description_vectorizer.fit(descriptions)
    joblib.dump(
        description_vectorizer,
        os.path.join(ML_MODELS_DIR, "description_vectorizer.joblib"),
    )

    # One-Hot Encoder for Cuisine
    # Reshape to 2D array as required by OneHotEncoder
    cuisine_encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    cuisine_encoder.fit(np.array(cuisines).reshape(-1, 1))
    joblib.dump(cuisine_encoder, os.path.join(ML_MODELS_DIR, "cuisine_encoder.joblib"))

    print("ML Models fitted and saved successfully.")

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
        recipe_ids = {}  # Store recipe IDs to use in Elasticsearch
        for i, recipe in enumerate(all_recipes_raw_data):
            try:
                recipe_id = str(uuid.uuid4())
                recipe_ids[i] = recipe_id  # Store the ID for Elasticsearch

                # --- Generate Feature Vector for Current Recipe ---
                # Transform text features
                title_vec = title_vectorizer.transform(
                    [safe_string(recipe.get("title", "")).strip()]
                ).toarray()
                ingredients_vec = ingredients_vectorizer.transform(
                    [" ".join(recipe.get("ingredients", [])).strip()]
                ).toarray()
                instructions_vec = instructions_vectorizer.transform(
                    [" ".join(recipe.get("instructions_list", [])).strip()]
                ).toarray()
                description_vec = description_vectorizer.transform(
                    [safe_string(recipe.get("description", "")).strip()]
                ).toarray()

                # Transform categorical features
                cuisine_vec = cuisine_encoder.transform(
                    np.array([safe_string(recipe.get("cuisine", "")).strip()]).reshape(
                        -1, 1
                    )
                )

                # Concatenate all vectors to form the final feature vector
                # Ensure all vectors are 2D arrays before concatenation, then flatten to 1D
                combined_feature_vector = np.concatenate(
                    [
                        title_vec.flatten(),
                        ingredients_vec.flatten(),
                        instructions_vec.flatten(),
                        description_vec.flatten(),
                        cuisine_vec.flatten(),
                    ]
                ).tolist()  # Convert to list for JSON serialization

                # Map JSON fields to database columns according to the new structure
                recipe_data = {
                    "id": recipe_id,
                    "title": safe_string(recipe.get("title", "")).strip(),
                    "description": safe_string(recipe.get("description", "")).strip(),
                    "recipe_url": safe_string(recipe.get("canonical_url", "")).strip(),
                    "image_url": safe_string(recipe.get("image", "")).strip(),
                    "ingredients": json.dumps(recipe.get("ingredients", [])),
                    "instructions": json.dumps(recipe.get("instructions_list", [])),
                    "category": safe_string(recipe.get("category", "")).strip(),
                    "cuisine": safe_string(recipe.get("cuisine", "")).strip(),
                    "site_name": safe_string(recipe.get("site_name", "")).strip(),
                    "keywords": json.dumps(recipe.get("keywords", [])),
                    "dietary_restrictions": json.dumps(
                        []
                    ),  # Not present in current data
                    "total_time": safe_int(recipe.get("total_time")),
                    "overall_rating": safe_float(recipe.get("ratings")),
                    "feature_vector": json.dumps(combined_feature_vector),
                }

                # Insert the data into the database
                cursor.execute(
                    """
                    INSERT INTO recipes (
                        id, title, description, recipe_url, image_url, ingredients, instructions,
                        category, cuisine, site_name, keywords, dietary_restrictions,
                        total_time, overall_rating, feature_vector
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        recipe_data["id"],
                        recipe_data["title"],
                        recipe_data["description"],
                        recipe_data["recipe_url"],
                        recipe_data["image_url"],
                        recipe_data["ingredients"],
                        recipe_data["instructions"],
                        recipe_data["category"],
                        recipe_data["cuisine"],
                        recipe_data["site_name"],
                        recipe_data["keywords"],
                        recipe_data["dietary_restrictions"],
                        recipe_data["total_time"],
                        recipe_data["overall_rating"],
                        recipe_data["feature_vector"],
                    ),
                )

                inserted_count += 1
                if inserted_count % 100 == 0:
                    print(f"Inserted {inserted_count} recipes...")

            except Exception as e:
                print(
                    f"Error inserting recipe (ID: {recipe_id if 'recipe_id' in locals() else 'N/A'}): {e}"
                )
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

            es.indices.create(index=ES_INDEX, body=mapping)
            print(f"Created Elasticsearch index: {ES_INDEX}")
        else:
            print(f"Elasticsearch index {ES_INDEX} already exists")

        # Index recipes in Elasticsearch
        indexed_count = 0
        for i, recipe in enumerate(all_recipes_raw_data):
            try:
                # Create document for Elasticsearch (only title and id)
                doc = {
                    "id": recipe_ids[i],  # Use the same ID as MariaDB
                    "title": safe_string(recipe.get("title", "")).strip(),
                }

                # Index the document
                es.index(index=ES_INDEX, body=doc)
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

    except Exception as e:
        print(f"Elasticsearch error: {e}")
        print("Make sure Elasticsearch is running and accessible")
