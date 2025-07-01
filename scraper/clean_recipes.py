import json
import re

RAW_JSON_FILEPATH = "./raw_recipes.json"
CLEANED_JSON_FILEPATH = "./cleaned_recipes.json"


def is_valid_string(value, min_length=1):
    """Check if a value is a valid non-empty string"""
    if not isinstance(value, str):
        return False
    return len(value.strip()) >= min_length


def is_valid_list(value, min_items=1):
    """Check if a value is a valid list with minimum items"""
    if not isinstance(value, list):
        return False
    return len(value) >= min_items


def is_valid_int(value, min_value=0):
    """Check if a value is a valid integer"""
    if not isinstance(value, (int, float)):
        return False
    return int(value) >= min_value


def is_valid_float(value, min_value=0.0, max_value=5.0):
    """Check if a value is a valid float within range"""
    if not isinstance(value, (int, float)):
        return False
    return min_value <= float(value) <= max_value


def is_valid_url(value):
    """Check if a value is a valid URL"""
    if not is_valid_string(value):
        return False
    # Basic URL validation
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return bool(url_pattern.match(value))


def validate_recipe(recipe):
    """Validate a recipe against database requirements"""
    errors = []

    # Required fields (NOT NULL in database)
    if not is_valid_string(recipe.get("title"), min_length=1):
        errors.append("Missing or invalid title")

    # Optional but important fields that should have valid data if present
    if recipe.get("canonical_url") and not is_valid_url(recipe.get("canonical_url")):
        errors.append("Invalid canonical_url")

    if recipe.get("image") and not is_valid_url(recipe.get("image")):
        errors.append("Invalid image URL")

    # Validate ingredients (should be a list)
    if not is_valid_list(recipe.get("ingredients"), min_items=1):
        errors.append("Missing or invalid ingredients list")
    else:
        # Check that ingredients are valid strings
        for i, ingredient in enumerate(recipe.get("ingredients", [])):
            if not is_valid_string(ingredient, min_length=1):
                errors.append(f"Invalid ingredient at index {i}")

    # Validate instructions (should be a list)
    if not is_valid_list(recipe.get("instructions_list"), min_items=1):
        errors.append("Missing or invalid instructions list")
    else:
        # Check that instructions are valid strings
        for i, instruction in enumerate(recipe.get("instructions_list", [])):
            if not is_valid_string(instruction, min_length=1):
                errors.append(f"Invalid instruction at index {i}")

    # Validate total_time if present
    if recipe.get("total_time") is not None and not is_valid_int(
        recipe.get("total_time"), min_value=1
    ):
        errors.append("Invalid total_time (should be positive integer)")

    # Validate ratings if present
    if recipe.get("ratings") is not None and not is_valid_float(
        recipe.get("ratings"), min_value=0.0, max_value=5.0
    ):
        errors.append("Invalid ratings (should be between 0.0 and 5.0)")

    # Validate keywords if present
    if recipe.get("keywords") is not None and not is_valid_list(
        recipe.get("keywords"), min_items=0
    ):
        errors.append("Invalid keywords (should be a list)")

    return errors


def clean_recipe(recipe):
    """Clean and normalize recipe data"""
    cleaned = recipe.copy()

    # For Zestful Kitchen, older recipes have an image size of 225x225 which we need to replace with 1000x1099
    website = recipe.get("host")
    img_url = recipe.get("image")
    if website == "zestfulkitchen.com" and img_url and "225x225" in img_url:
        cleaned["image"] = img_url.replace("225x225", "1000x1099")

    # Ensure ingredients is a list
    if not isinstance(cleaned.get("ingredients"), list):
        cleaned["ingredients"] = []

    # Ensure instructions_list is a list
    if not isinstance(cleaned.get("instructions_list"), list):
        cleaned["instructions_list"] = []

    # Ensure keywords is a list
    if not isinstance(cleaned.get("keywords"), list):
        cleaned["keywords"] = []

    # Clean string fields
    for field in [
        "title",
        "description",
        "canonical_url",
        "image",
        "category",
        "cuisine",
        "site_name",
    ]:
        if field in cleaned and not is_valid_string(cleaned[field]):
            cleaned[field] = None

    # Clean numeric fields
    if "total_time" in cleaned and not is_valid_int(cleaned["total_time"], min_value=1):
        cleaned["total_time"] = None

    if "ratings" in cleaned and not is_valid_float(
        cleaned["ratings"], min_value=0.0, max_value=5.0
    ):
        cleaned["ratings"] = None

    return cleaned


# Load the recipes
print("Loading recipes...")
with open(RAW_JSON_FILEPATH, "r") as f:
    recipes: dict[str, dict] = json.load(f)

print(f"Loaded {len(recipes)} recipes")

# Clean and validate recipes
cleaned_recipes = {}
invalid_recipes = []
validation_stats = {"total": len(recipes), "valid": 0, "invalid": 0, "errors": {}}

for url, recipe in recipes.items():
    # Clean the recipe first
    cleaned_recipe = clean_recipe(recipe)

    # Validate the cleaned recipe
    errors = validate_recipe(cleaned_recipe)

    if errors:
        invalid_recipes.append(
            {"url": url, "title": recipe.get("title", "Unknown"), "errors": errors}
        )
        validation_stats["invalid"] += 1

        # Track error types for reporting
        for error in errors:
            if error not in validation_stats["errors"]:
                validation_stats["errors"][error] = 0
            validation_stats["errors"][error] += 1
    else:
        cleaned_recipes[url] = cleaned_recipe
        validation_stats["valid"] += 1

# Print validation results
print("\nValidation Results:")
print(f"Total recipes: {validation_stats['total']}")
print(f"Valid recipes: {validation_stats['valid']}")
print(f"Invalid recipes: {validation_stats['invalid']}")
print(
    f"Success rate: {(validation_stats['valid'] / validation_stats['total'] * 100):.1f}%"
)

if validation_stats["errors"]:
    print("\nError breakdown:")
    for error, count in sorted(
        validation_stats["errors"].items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {error}: {count} recipes")

# Save the cleaned recipes
print(f"\nSaving {len(cleaned_recipes)} valid recipes...")
with open(CLEANED_JSON_FILEPATH, "w") as f:
    json.dump(cleaned_recipes, f, indent=4)

print(f"Cleaned recipes saved to {CLEANED_JSON_FILEPATH}")

# Optionally save invalid recipes for analysis
if invalid_recipes:
    invalid_filepath = "./invalid_recipes.json"
    with open(invalid_filepath, "w") as f:
        json.dump(invalid_recipes, f, indent=4)
    print(f"Invalid recipes saved to {invalid_filepath} for analysis")
