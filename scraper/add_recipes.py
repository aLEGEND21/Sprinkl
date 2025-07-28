#!/usr/bin/env python3
"""Add recipes from JSON file to database via API"""

import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

POST_RECIPE_URL = os.getenv("POST_RECIPE_URL")


def add_recipes_from_file(file_path: str) -> None:
    """Add recipes from JSON file to database using batch API"""

    with open(file_path, "r") as f:
        recipes: dict[str, dict] = json.load(f)

    # Convert dict to list of recipes
    recipe_list = list(recipes.values())

    # Send all recipes in a single batch request
    resp = requests.post(POST_RECIPE_URL, json=recipe_list)
    data = resp.json()

    # Truncate the recipe IDs since there may be too many
    if "recipe_ids" in data:
        data["recipe_ids"] = data["recipe_ids"][:10]
    print(json.dumps(data, indent=4))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python add_recipes.py <recipes_file.json>")
        sys.exit(1)

    add_recipes_from_file(sys.argv[1])
