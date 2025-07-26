import argparse
import json
import time

import recipe_scrapers
import undetected_chromedriver as uc
from bs4 import BeautifulSoup


def parse_arguments():
    """
    Parse command line arguments for sitemap URL and raw JSON filepath.
    """
    parser = argparse.ArgumentParser(description="Scrape recipes from a sitemap URL")
    parser.add_argument(
        "-u",
        "--sitemap-url",
        type=str,
        required=True,
        help="URL of the sitemap to scrape",
    )
    parser.add_argument(
        "-f",
        "--output-file",
        type=str,
        required=True,
        help="Filepath for the raw JSON output",
    )
    return parser.parse_args()


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
    start = time.time()
    driver.get(url)
    recipe = recipe_scrapers.scrape_html(driver.page_source, url)
    delta = time.time() - start
    print(f"[{delta:.2f}s] Driver scraped {url}")
    return recipe.to_json()


# Parse command line arguments
args = parse_arguments()
SITEMAP_URL = args.sitemap_url
RAW_JSON_FILEPATH = args.output_file

# Load the driver. Do not use headless mode as non-headless performs better.
options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = uc.Chrome(options=options)

# Load all page links from the sitemap URL
recipe_urls = load_page_links(driver, SITEMAP_URL)
print(f"Loaded {len(recipe_urls)} recipe URLs")

# Load existing recipes or create empty dict if file doesn't exist
try:
    with open(RAW_JSON_FILEPATH, "r") as f:
        recipes: dict[str, dict] = json.load(f)
except FileNotFoundError:
    print(f"Creating new file: {RAW_JSON_FILEPATH}")
    recipes: dict[str, dict] = {}

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

except KeyboardInterrupt:
    print("Keyboard interrupt detected. Exiting...")

except Exception as e:
    print(e)

finally:
    with open(RAW_JSON_FILEPATH, "w") as f:
        json.dump(recipes, f, indent=4)
    driver.quit()
