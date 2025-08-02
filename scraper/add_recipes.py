#!/usr/bin/env python3
"""Add recipes from JSON file to database via API"""

import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

POST_RECIPE_URL = os.getenv("POST_RECIPE_URL")
BATCH_SIZE = 500


def add_recipes_from_file(file_path: str) -> None:
    """Add recipes from JSON file to database using batch API"""

    with open(file_path, "r") as f:
        recipes: dict[str, dict] = json.load(f)

    # Convert dict to list of recipes
    recipe_list = list(recipes.values())

    # Send all recipes in batches
    print(
        f"Sending {len(recipe_list)} recipes to API using {len(recipe_list) // BATCH_SIZE + 1} batches"
    )
    for i in range(0, len(recipe_list), BATCH_SIZE):
        current_batch = i // BATCH_SIZE + 1
        batch = recipe_list[i : i + BATCH_SIZE]
        resp = requests.post(POST_RECIPE_URL, json=batch)
        data = resp.json()

        # Truncate response to first 5 recipe IDs
        if "recipe_ids" in data:
            data["recipe_ids"] = data["recipe_ids"][:5]

        print(f"Response from batch {current_batch}:")
        print(json.dumps(data, indent=4))
        print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python add_recipes.py <recipes_file.json>")
        sys.exit(1)

    add_recipes_from_file(sys.argv[1])
