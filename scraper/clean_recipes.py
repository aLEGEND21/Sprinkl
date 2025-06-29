import json


# Load the recipes
with open("recipes.json", "r") as f:
    recipes: dict[str, dict] = json.load(f)


# For Zestful Kitchen, older recipes have an image size of 225x225 which we need to replace with 1000x1099
count = 0
for url, recipe in recipes.items():
    website = recipe.get("host")
    img_url = recipe.get("image")
    if website == "zestfulkitchen.com" and img_url and "225x225" in img_url:
        recipe["image"] = img_url.replace("225x225", "1000x1099")
        count += 1
print(f"Replaced {count} images for Zestful Kitchen")


# Save the recipes
with open("recipes.json", "w") as f:
    json.dump(recipes, f, indent=4)
