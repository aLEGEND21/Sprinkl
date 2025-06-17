# init.py - Add the recipes from the .csv file to the database
# This file is not automatically run when the container is started, unlike init.sql
# Instead, run this script manually after the container is started from the db_init directory

import csv
import json
import os
import uuid

import joblib  # To save/load scikit-learn models
import numpy as np
import pymysql
from dotenv import load_dotenv
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

# Path to your CSV file
CSV_FILE_PATH = "init_dataset.csv"

# Directory to save fitted ML models (vectorizers, encoders)
ML_MODELS_DIR = (
    "../ml_models"  # Store in project root since the API will use these models
)
os.makedirs(ML_MODELS_DIR, exist_ok=True)  # Create directory if it doesn't exist


# --- Helper Functions ---
def parse_ingredients(ingredients_str):
    """Parse ingredients string and return as JSON array"""
    if not ingredients_str or ingredients_str.strip() == "":
        return json.dumps([])

    # Split by comma and clean up each ingredient
    ingredients = [ingredient.strip() for ingredient in ingredients_str.split(",")]
    return json.dumps(ingredients)


def parse_cleaned_ingredients(cleaned_ingredients_str):
    """Parse cleaned ingredients string and return as JSON array"""
    if not cleaned_ingredients_str or cleaned_ingredients_str.strip() == "":
        return json.dumps([])

    try:
        if cleaned_ingredients_str.startswith("[") and cleaned_ingredients_str.endswith(
            "]"
        ):
            # Use json.loads if it's proper JSON format
            ingredients = json.loads(cleaned_ingredients_str.replace("'", '"'))
            return json.dumps(ingredients)
    except json.JSONDecodeError:
        pass  # Not a valid JSON string, proceed to comma split

    # Otherwise split by comma
    ingredients = [
        ingredient.strip() for ingredient in cleaned_ingredients_str.split(",")
    ]
    return json.dumps(ingredients)


def safe_int(value):
    """Safely convert value to int, return None if conversion fails"""
    try:
        return int(float(value)) if value and value.strip() != "" else None
    except (ValueError, TypeError):
        return None


# --- Main Script ---
if __name__ == "__main__":
    all_recipes_raw_data = []  # To store all data for fitting vectorizers/encoders

    # First pass: Read all data to fit the vectorizers/encoders
    print(f"Reading CSV file: {CSV_FILE_PATH} for ML model training...")
    try:
        with open(CSV_FILE_PATH, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                all_recipes_raw_data.append(row)
        print(f"Finished reading {len(all_recipes_raw_data)} recipes from CSV.")
    except FileNotFoundError:
        print(f"Error: CSV file not found at {CSV_FILE_PATH}")
        exit()
    except Exception as e:
        print(f"Error reading CSV for ML model training: {e}")
        exit()

    # Prepare data for TF-IDF and One-Hot Encoding
    recipe_names = [
        row.get("TranslatedRecipeName", "").strip() for row in all_recipes_raw_data
    ]
    ingredients_text = [
        row.get("TranslatedIngredients", "").strip() for row in all_recipes_raw_data
    ]
    instructions_text = [
        row.get("TranslatedInstructions", "").strip() for row in all_recipes_raw_data
    ]
    cuisines = [row.get("Cuisine", "").strip() for row in all_recipes_raw_data]

    # --- Initialize and Fit ML Models ---
    print("Fitting TF-IDF Vectorizers and One-Hot Encoders...")

    # TF-IDF for Recipe Name
    name_vectorizer = TfidfVectorizer(
        stop_words="english", max_features=1000
    )  # Limit features to avoid very high dimensionality
    name_vectorizer.fit(recipe_names)
    joblib.dump(name_vectorizer, os.path.join(ML_MODELS_DIR, "name_vectorizer.joblib"))

    # TF-IDF for Ingredients (using 'cleaned_ingredients' if preferred, or 'TranslatedIngredients')
    # Assuming 'Cleaned-Ingredients' can be processed for better feature representation
    cleaned_ingredients_for_tfidf = [
        " ".join(
            json.loads(parse_cleaned_ingredients(row.get("Cleaned-Ingredients", "")))
        )
        for row in all_recipes_raw_data
    ]
    ingredients_vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
    ingredients_vectorizer.fit(
        ingredients_text
    )  # Using raw translated ingredients as it's a single string
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
        for i, row in enumerate(
            all_recipes_raw_data
        ):  # Iterate through already loaded data
            try:
                recipe_id = str(uuid.uuid4())

                # --- Generate Feature Vector for Current Recipe ---
                # Transform text features
                name_vec = name_vectorizer.transform(
                    [row.get("TranslatedRecipeName", "").strip()]
                ).toarray()
                ingredients_vec = ingredients_vectorizer.transform(
                    [row.get("TranslatedIngredients", "").strip()]
                ).toarray()
                instructions_vec = instructions_vectorizer.transform(
                    [row.get("TranslatedInstructions", "").strip()]
                ).toarray()

                # Transform categorical features
                cuisine_vec = cuisine_encoder.transform(
                    np.array([row.get("Cuisine", "").strip()]).reshape(-1, 1)
                )

                # Concatenate all vectors to form the final feature vector
                # Ensure all vectors are 2D arrays before concatenation, then flatten to 1D
                combined_feature_vector = np.concatenate(
                    [
                        name_vec.flatten(),
                        ingredients_vec.flatten(),
                        instructions_vec.flatten(),
                        cuisine_vec.flatten(),
                    ]
                ).tolist()  # Convert to list for JSON serialization

                # Map CSV columns to database columns
                recipe_data = {
                    "id": recipe_id,
                    "recipe_name": row.get("TranslatedRecipeName", "").strip(),
                    "ingredient_measurements": parse_ingredients(
                        row.get("TranslatedIngredients", "")
                    ),
                    "time_mins": safe_int(row.get("TotalTimeInMins")),
                    "cuisine": row.get("Cuisine", "").strip(),
                    "instructions": row.get("TranslatedInstructions", "").strip(),
                    "recipe_url": row.get("URL", "").strip(),
                    "ingredient_list": parse_cleaned_ingredients(
                        row.get("Cleaned-Ingredients", "")
                    ),
                    "image_url": row.get("image-url", "").strip(),
                    "ingredient_count": safe_int(row.get("Ingredient-count")),
                    "feature_vector": json.dumps(
                        combined_feature_vector
                    ),  # Now contains the actual vector
                }

                # Insert the data into the database
                cursor.execute(
                    """
                    INSERT INTO recipes (
                        id, recipe_name, ingredient_measurements, time_mins, cuisine,
                        instructions, recipe_url, ingredient_list, image_url,
                        ingredient_count, feature_vector
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        recipe_data["id"],
                        recipe_data["recipe_name"],
                        recipe_data["ingredient_measurements"],
                        recipe_data["time_mins"],
                        recipe_data["cuisine"],
                        recipe_data["instructions"],
                        recipe_data["recipe_url"],
                        recipe_data["ingredient_list"],
                        recipe_data["image_url"],
                        recipe_data["ingredient_count"],
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
                print(f"Row data causing error: {row}")
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
