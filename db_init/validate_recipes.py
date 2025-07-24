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
DB_NAME = os.getenv("MARIADB_DATABASE")
DB_USER = os.getenv("MARIADB_USER")
DB_PASSWORD = os.getenv("MARIADB_PASSWORD")
DB_HOST = "localhost"
DB_PORT = 3306


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

    # Add recipe title
    if recipe["title"]:
        features.append(clean_text(recipe["title"]))

    # Add description
    if recipe["description"]:
        features.append(clean_text(recipe["description"]))

    # Add ingredients
    if recipe["ingredients"]:
        try:
            ingredients = json.loads(recipe["ingredients"])
            if isinstance(ingredients, list):
                features.extend([clean_text(ing) for ing in ingredients])
        except (json.JSONDecodeError, TypeError):
            pass

    # Add instructions
    if recipe["instructions"]:
        try:
            instructions = json.loads(recipe["instructions"])
            if isinstance(instructions, list):
                features.extend([clean_text(inst) for inst in instructions])
        except (json.JSONDecodeError, TypeError):
            pass

    # Add cuisine
    if recipe["cuisine"]:
        features.append(clean_text(recipe["cuisine"]))

    # Add category
    if recipe["category"]:
        features.append(clean_text(recipe["category"]))

    # Add keywords
    if recipe["keywords"]:
        try:
            keywords = json.loads(recipe["keywords"])
            if isinstance(keywords, list):
                features.extend([clean_text(keyword) for keyword in keywords])
        except (json.JSONDecodeError, TypeError):
            pass

    # Add cooking time category
    if recipe["total_time"]:
        if recipe["total_time"] <= 30:
            features.append("quick meal")
        elif recipe["total_time"] <= 60:
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
        cursor.execute(
            """
            SELECT id, title, description, recipe_url, image_url, ingredients, instructions,
                   category, cuisine, site_name, keywords, dietary_restrictions,
                   total_time, overall_rating
            FROM recipes 
            WHERE title IS NOT NULL AND title != ''
        """
        )

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
        print(f"Title: {target_recipe['title']}")
        if target_recipe["description"]:
            print(
                f"Description: {target_recipe['description'][:100]}{'...' if len(target_recipe['description']) > 100 else ''}"
            )
        print(f"Cuisine: {target_recipe['cuisine']}")
        if target_recipe["category"]:
            print(f"Category: {target_recipe['category']}")
        if target_recipe["site_name"]:
            print(f"Site: {target_recipe['site_name']}")
        print(
            f"Total Time: {target_recipe['total_time']} minutes"
            if target_recipe["total_time"]
            else "Total Time: Not specified"
        )
        if target_recipe["overall_rating"]:
            print(f"Rating: {target_recipe['overall_rating']}/5.0")

        # Show ingredients
        if target_recipe["ingredients"]:
            try:
                ingredients = json.loads(target_recipe["ingredients"])
                if isinstance(ingredients, list) and ingredients:
                    print(
                        f"Ingredients: {', '.join(ingredients[:5])}{'...' if len(ingredients) > 5 else ''}"
                    )
            except (json.JSONDecodeError, TypeError):
                pass

        # Show keywords
        if target_recipe["keywords"]:
            try:
                keywords = json.loads(target_recipe["keywords"])
                if isinstance(keywords, list) and keywords:
                    print(
                        f"Keywords: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}"
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
        print("TOP 5 MOST SIMILAR RECIPES:")
        print("=" * 60)

        for i, (recipe, similarity_score) in enumerate(similar_recipes, 1):
            print(f"\n{i}. {recipe['title']}")
            print(f"   ID: {recipe['id']}")
            print(f"   Similarity Score: {similarity_score:.4f}")
            print(f"   Cuisine: {recipe['cuisine']}")
            if recipe["category"]:
                print(f"   Category: {recipe['category']}")
            if recipe["total_time"]:
                print(f"   Total Time: {recipe['total_time']} minutes")
            if recipe["overall_rating"]:
                print(f"   Rating: {recipe['overall_rating']}/5.0")

            # Show some ingredients
            if recipe["ingredients"]:
                try:
                    ingredients = json.loads(recipe["ingredients"])
                    if isinstance(ingredients, list) and ingredients:
                        print(
                            f"   Key Ingredients: {', '.join(ingredients[:3])}{'...' if len(ingredients) > 3 else ''}"
                        )
                except (json.JSONDecodeError, TypeError):
                    pass

            # Show some keywords
            if recipe["keywords"]:
                try:
                    keywords = json.loads(recipe["keywords"])
                    if isinstance(keywords, list) and keywords:
                        print(
                            f"   Keywords: {', '.join(keywords[:3])}{'...' if len(keywords) > 3 else ''}"
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
