from bs4 import BeautifulSoup
import recipe_scrapers
import undetected_chromedriver as uc
import json
import time


SITEMAP_URL = "https://zestfulkitchen.com/post-sitemap.xml"


def load_page_links(driver: uc.Chrome, sitemap_url: str) -> list[str]:
    """
    Loads all page links from a sitemap.
    """
    driver.get(sitemap_url)
    time.sleep(0.5)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    recipe_urls = []
    for row in soup.select("#sitemap tbody tr"):
        link = row.find("a")
        if link:
            recipe_urls.append(link.get("href"))

    return recipe_urls


def scrape_recipe(driver: uc.Chrome, url: str) -> dict:
    """
    Scrape a recipe from a URL.
    """
    driver.get(url)
    print(f"Driver scraped {url}")
    recipe = recipe_scrapers.scrape_html(driver.page_source, url)
    return recipe.to_json()


# Load the driver. Do not use headless mode as non-headless performs better.
options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = uc.Chrome(options=options)


# Load all page links from the sitemap URL
recipe_urls = load_page_links(driver, SITEMAP_URL)
print(f"Loaded {len(recipe_urls)} recipe URLs")

# Load existing recipes
with open("recipes.json", "r") as f:
    recipes: dict[str, dict] = json.load(f)

# Scrape all recipes, skipping the ones that are already in the database
try:
    for i, url in enumerate(recipe_urls):
        if url in recipes:
            continue
        recipe = scrape_recipe(driver, url)
        recipes[url] = recipe
        time.sleep(0.25)

        if i % 10 == 0:
            print(f"Scraped {i} recipes")
    print(f"Successfully scraped {len(recipes)} recipes")

except Exception as e:
    print(e)

finally:
    with open("recipes.json", "w") as f:
        json.dump(recipes, f, indent=4)
    driver.quit()
