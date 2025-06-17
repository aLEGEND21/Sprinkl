# validate_recipes.py - Validate the recipes in the database and the similarity script
# This script selects a random recipe and finds the 5 most similar recipes

import json
import os
import random
import re

import pymysql
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load the database information
load_dotenv()
DB_NAME = os.getenv("MARIADB_DATABASE", "foodapp_db")
DB_USER = os.getenv("MARIADB_USER", "root")
DB_PASSWORD = os.getenv("MARIADB_PASSWORD")
DB_HOST = os.getenv("MARIADB_HOST", "localhost")
DB_PORT = int(os.getenv("MARIADB_PORT", "3306"))


def clean_text(text):
    """Clean and normalize text for similarity comparison"""
    if not text:
        return ""
    # Convert to lowercase and remove special characters
    text = re.sub(r"[^a-zA-Z\s]", " ", str(text).lower())
    # Remove extra whitespace
    text = " ".join(text.split())
    return text


def get_recipe_features(recipe):
    """Extract features from a recipe for similarity comparison"""
    features = []

    # Add recipe name
    if recipe["recipe_name"]:
        features.append(clean_text(recipe["recipe_name"]))

    # Add ingredients
    if recipe["ingredient_list"]:
        try:
            ingredients = json.loads(recipe["ingredient_list"])
            if isinstance(ingredients, list):
                features.extend([clean_text(ing) for ing in ingredients])
        except (json.JSONDecodeError, TypeError):
            pass

    # Add cuisine
    if recipe["cuisine"]:
        features.append(clean_text(recipe["cuisine"]))

    # Add cooking time category
    if recipe["time_mins"]:
        if recipe["time_mins"] <= 30:
            features.append("quick meal")
        elif recipe["time_mins"] <= 60:
            features.append("medium cook time")
        else:
            features.append("long cook time")

    return " ".join(features)


def calculate_similarity_matrix(recipes):
    """Calculate similarity matrix using TF-IDF and cosine similarity"""
    print("Calculating recipe similarities...")

    # Extract features for all recipes
    recipe_texts = []
    for recipe in recipes:
        features = get_recipe_features(recipe)
        recipe_texts.append(features)

    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer(
        max_features=1000, stop_words="english", ngram_range=(1, 2)
    )

    tfidf_matrix = vectorizer.fit_transform(recipe_texts)

    # Calculate cosine similarity
    similarity_matrix = cosine_similarity(tfidf_matrix)

    return similarity_matrix


def find_similar_recipes(
    target_recipe, all_recipes, similarity_matrix, target_index, top_k=5
):
    """Find the most similar recipes to the target recipe"""

    # Get similarity scores for the target recipe
    similarity_scores = similarity_matrix[target_index]

    # Create list of (recipe, similarity_score) tuples, excluding the target recipe itself
    recipe_similarities = []
    for i, recipe in enumerate(all_recipes):
        if i != target_index:  # Exclude the target recipe
            recipe_similarities.append((recipe, similarity_scores[i]))

    # Sort by similarity score (descending)
    recipe_similarities.sort(key=lambda x: x[1], reverse=True)

    # Return top k similar recipes
    return recipe_similarities[:top_k]


def main():
    try:
        # Connect to the MariaDB database
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4",
        )
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        print(f"Connected to MariaDB database: {DB_NAME}")

        # Fetch all recipes from the database
        cursor.execute("""
            SELECT id, recipe_name, ingredient_list, cuisine, time_mins, ingredient_count
            FROM recipes 
            WHERE recipe_name IS NOT NULL AND recipe_name != ''
        """)

        recipes = cursor.fetchall()

        if not recipes:
            print("No recipes found in the database!")
            return

        print(f"Found {len(recipes)} recipes in the database")

        # Select a random recipe
        target_recipe = random.choice(recipes)
        target_index = recipes.index(target_recipe)

        print(f"\n{'=' * 60}")
        print("SELECTED RANDOM RECIPE:")
        print("=" * 60)
        print(f"ID: {target_recipe['id']}")
        print(f"Name: {target_recipe['recipe_name']}")
        print(f"Cuisine: {target_recipe['cuisine']}")
        print(
            f"Cooking Time: {target_recipe['time_mins']} minutes"
            if target_recipe["time_mins"]
            else "Cooking Time: Not specified"
        )
        print(
            f"Ingredient Count: {target_recipe['ingredient_count']}"
            if target_recipe["ingredient_count"]
            else "Ingredient Count: Not specified"
        )

        # Show ingredients
        if target_recipe["ingredient_list"]:
            try:
                ingredients = json.loads(target_recipe["ingredient_list"])
                if isinstance(ingredients, list) and ingredients:
                    print(
                        f"Ingredients: {', '.join(ingredients[:5])}{'...' if len(ingredients) > 5 else ''}"
                    )
            except (json.JSONDecodeError, TypeError):
                pass

        # Calculate similarity matrix
        similarity_matrix = calculate_similarity_matrix(recipes)

        # Find similar recipes
        similar_recipes = find_similar_recipes(
            target_recipe, recipes, similarity_matrix, target_index, 5
        )

        print(f"\n{'=' * 60}")
        print("TOP 10 MOST SIMILAR RECIPES:")
        print("=" * 60)

        for i, (recipe, similarity_score) in enumerate(similar_recipes, 1):
            print(f"\n{i}. {recipe['recipe_name']}")
            print(f"   ID: {recipe['id']}")
            print(f"   Similarity Score: {similarity_score:.4f}")
            print(f"   Cuisine: {recipe['cuisine']}")
            if recipe["time_mins"]:
                print(f"   Cooking Time: {recipe['time_mins']} minutes")
            if recipe["ingredient_count"]:
                print(f"   Ingredient Count: {recipe['ingredient_count']}")

            # Show some ingredients
            if recipe["ingredient_list"]:
                try:
                    ingredients = json.loads(recipe["ingredient_list"])
                    if isinstance(ingredients, list) and ingredients:
                        print(
                            f"   Key Ingredients: {', '.join(ingredients[:3])}{'...' if len(ingredients) > 3 else ''}"
                        )
                except (json.JSONDecodeError, TypeError):
                    pass

        print(f"\n{'=' * 60}")
        print("Analysis complete!")

    except pymysql.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if "conn" in locals():
            cursor.close()
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main()
