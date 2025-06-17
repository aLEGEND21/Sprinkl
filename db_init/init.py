# init.py - Add the recipes from the .csv file to the database
# This file is not automatically run when the container is started, unlike init.sql
# Instead, to populate the recipes table, run this script manually after the container is started

import csv
import json
import uuid
from dotenv import load_dotenv
import os
import pymysql


# Load the database information
load_dotenv()
DB_NAME = os.getenv("MARIADB_DATABASE")
DB_USER = os.getenv("MARIADB_USER")
DB_PASSWORD = os.getenv("MARIADB_PASSWORD")
DB_HOST = os.getenv("MARIADB_HOST", "localhost")
DB_PORT = int(os.getenv("MARIADB_PORT", "3306"))

def parse_ingredients(ingredients_str):
    """Parse ingredients string and return as JSON array"""
    if not ingredients_str or ingredients_str.strip() == "":
        return json.dumps([])
    
    # Split by comma and clean up each ingredient
    ingredients = [ingredient.strip() for ingredient in ingredients_str.split(',')]
    return json.dumps(ingredients)

def parse_cleaned_ingredients(cleaned_ingredients_str):
    """Parse cleaned ingredients string and return as JSON array"""
    if not cleaned_ingredients_str or cleaned_ingredients_str.strip() == "":
        return json.dumps([])
    
    # If it's already in array format like ['item1', 'item2'], evaluate it safely
    try:
        if cleaned_ingredients_str.startswith('[') and cleaned_ingredients_str.endswith(']'):
            # Use json.loads if it's proper JSON format
            ingredients = json.loads(cleaned_ingredients_str.replace("'", '"'))
            return json.dumps(ingredients)
    except:
        pass
    
    # Otherwise split by comma
    ingredients = [ingredient.strip() for ingredient in cleaned_ingredients_str.split(',')]
    return json.dumps(ingredients)

def safe_int(value):
    """Safely convert value to int, return None if conversion fails"""
    try:
        return int(float(value)) if value and value.strip() != "" else None
    except (ValueError, TypeError):
        return None

# Connect to the MariaDB database
try:
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    print(f"Connected to MariaDB database: {DB_NAME}")
    
    # Read the CSV file and insert the data into the database
    csv_file_path = 'init_dataset.csv'  # Adjust path as needed
    
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        inserted_count = 0
        for row in reader:
            try:
                # Generate a unique ID for each recipe
                recipe_id = str(uuid.uuid4())
                
                # Map CSV columns to database columns
                recipe_data = {
                    'id': recipe_id,
                    'recipe_name': row.get('TranslatedRecipeName', '').strip(),
                    'ingredient_measurements': parse_ingredients(row.get('TranslatedIngredients', '')),
                    'time_mins': safe_int(row.get('TotalTimeInMins')),
                    'cuisine': row.get('Cuisine', '').strip(),
                    'instructions': row.get('TranslatedInstructions', '').strip(),
                    'recipe_url': row.get('URL', '').strip(),
                    'ingredient_list': parse_cleaned_ingredients(row.get('Cleaned-Ingredients', '')),
                    'image_url': row.get('image-url', '').strip(),
                    'ingredient_count': safe_int(row.get('Ingredient-count')),
                    'feature_vector': json.dumps([])  # Initialize empty, to be filled by ML backend
                }
                
                # Insert the data into the database
                cursor.execute("""
                    INSERT INTO recipes (
                        id, recipe_name, ingredient_measurements, time_mins, cuisine, 
                        instructions, recipe_url, ingredient_list, image_url, 
                        ingredient_count, feature_vector
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    recipe_data['id'],
                    recipe_data['recipe_name'],
                    recipe_data['ingredient_measurements'],
                    recipe_data['time_mins'],
                    recipe_data['cuisine'],
                    recipe_data['instructions'],
                    recipe_data['recipe_url'],
                    recipe_data['ingredient_list'],
                    recipe_data['image_url'],
                    recipe_data['ingredient_count'],
                    recipe_data['feature_vector']
                ))
                
                inserted_count += 1
                if inserted_count % 100 == 0:
                    print(f"Inserted {inserted_count} recipes...")
                    
            except Exception as e:
                print(f"Error inserting recipe: {e}")
                print(f"Row data: {row}")
                continue
    
    # Commit the changes
    conn.commit()
    print(f"Successfully inserted {inserted_count} recipes into the database!")
    
except pymysql.Error as e:
    print(f"Database error: {e}")
except FileNotFoundError:
    print(f"CSV file not found: {csv_file_path}")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        cursor.close()
        conn.close()
        print("Database connection closed.")