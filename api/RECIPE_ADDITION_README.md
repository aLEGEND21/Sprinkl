# Recipe Addition Guide

This guide explains how to add new recipes to your FoodApp database while automatically calculating feature vectors for the recommendation system.

## Overview

The new recipe addition system provides:

- **Automatic feature vector calculation** using pre-trained ML models
- **Centralized database operations** through DatabaseManager
- **Centralized search operations** through ElasticsearchService
- **Database and Elasticsearch integration** for seamless storage and search
- **Error handling** and validation
- **RESTful API endpoints** for easy integration

## Architecture

The recipe addition system follows a clean separation of concerns:

- **RecipeService**: Handles ML model loading, feature vector calculation, and orchestrates operations
- **DatabaseManager**: Manages all database operations (insertion, retrieval, etc.)
- **ElasticsearchService**: Handles all search indexing and search operations
- **FastAPI Endpoints**: Provide RESTful API interface

## Prerequisites

Before adding new recipes, ensure:

1. **ML Models are initialized**: Run the database initialization script first:

   ```bash
   cd db_init
   python init.py
   ```

2. **API is running**: Start your FastAPI application:

   ```bash
   cd api
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. **Dependencies are installed**: All required packages are already in `requirements.txt`

4. **Docker Volume Setup**: The `ml_models` directory is shared between containers:
   - **Development**: Use `docker-compose up` to start all services
   - **Production**: Use `docker-compose -f compose.prod.yml up` to start production services
   - The `ml_models` volume ensures both API and db_init containers can access the same ML models

## Docker Setup

The application uses Docker volumes to share ML models between containers:

### Volume Configuration

- **`ml_models`**: Shared volume for ML models between API and db_init containers
- **Path**: `/app/ml_models` within containers
- **Purpose**: Allows both containers to read/write ML models (vectorizers, encoders)

### Development Setup

```bash
# Start all services with shared volumes
docker-compose up

# Or start specific services
docker-compose up mariadb elasticsearch init api
```

### Production Setup

```bash
# Start production services
docker-compose -f compose.prod.yml up

# Or start specific services
docker-compose -f compose.prod.yml up mariadb elasticsearch api
```

### Volume Management

```bash
# List volumes
docker volume ls

# Inspect ml_models volume
docker volume inspect foodapp_ml_models

# Remove volume (if needed)
docker volume rm foodapp_ml_models
```

## API Endpoints

### Add Multiple Recipes

**Endpoint**: `POST /recipes`

**Request Body**: Array of recipe objects

```json
[
  {
    "id": "uuid-string-1",
    "title": "Recipe Title 1",
    "description": "Optional description",
    "recipe_url": "https://example.com/recipe1",
    "image_url": "https://example.com/image1.jpg",
    "ingredients": ["ingredient 1", "ingredient 2"],
    "instructions": ["step 1", "step 2"],
    "category": "Main Course",
    "cuisine": "Italian",
    "site_name": "Recipe Site",
    "keywords": ["keyword1", "keyword2"],
    "dietary_restrictions": ["vegetarian"],
    "total_time": 30,
    "overall_rating": 4.5
  },
  {
    "id": "uuid-string-2",
    "title": "Recipe Title 2",
    "ingredients": ["ingredient 3", "ingredient 4"],
    "instructions": ["step 1", "step 2"],
    "cuisine": "Mexican"
  }
]
```

**Required Fields** (per recipe):

- `id`: Recipe ID (string) - must be unique
- `title`: Recipe title (string)
- `ingredients`: List of ingredients (array of strings)
- `instructions`: List of cooking steps (array of strings)

**Optional Fields** (per recipe):

- `description`: Recipe description
- `recipe_url`: Source URL
- `image_url`: Image URL
- `category`: Recipe category
- `cuisine`: Cuisine type
- `site_name`: Source website name
- `keywords`: List of keywords
- `dietary_restrictions`: List of dietary restrictions
- `total_time`: Cooking time in minutes
- `overall_rating`: Rating (0.0-5.0)

**Response**:

```json
{
  "message": "Successfully processed 100 recipes",
  "added_count": 95,
  "skipped_count": 5,
  "recipe_ids": ["uuid-string-1", "uuid-string-2", ...],
  "errors": [],
  "sample_recipe_id": "uuid-string-1",
  "sample_recipe_title": "Chocolate Chip Cookies",
  "similar_recipe_id": "similar-uuid",
  "similar_recipe_title": "Oatmeal Raisin Cookies",
  "similarity_score": 0.85,
  "total_time_seconds": 2.45
}
```

**Response Fields**:

- **message**: Summary of the operation
- **added_count**: Number of recipes successfully added
- **skipped_count**: Number of recipes skipped (duplicates)
- **recipe_ids**: List of successfully added recipe IDs
- **errors**: List of any errors encountered
- **sample_recipe_id**: ID of the randomly selected recipe for similarity analysis
- **sample_recipe_title**: Title of the randomly selected recipe
- **similar_recipe_id**: ID of the most similar recipe found in the database
- **similar_recipe_title**: Title of the most similar recipe
- **similarity_score**: Similarity score between 0 and 1 (higher = more similar)
- **total_time_seconds**: Total time elapsed for the entire operation in seconds

## Usage Examples

### Python Example

```python
import requests

# Add multiple recipes
recipes_data = [
    {
        "id": "uuid-1",
        "title": "Chocolate Chip Cookies",
        "description": "Classic homemade cookies",
        "ingredients": ["2 cups flour", "1 cup butter", "1 cup sugar"],
        "instructions": ["Preheat oven", "Mix ingredients", "Bake for 10 minutes"],
        "cuisine": "American",
        "total_time": 30
    },
    {
        "id": "uuid-2",
        "title": "Pasta Carbonara",
        "description": "Traditional Italian pasta",
        "ingredients": ["pasta", "eggs", "bacon", "cheese"],
        "instructions": ["Cook pasta", "Fry bacon", "Mix with eggs"],
        "cuisine": "Italian",
        "total_time": 20
    }
]

response = requests.post("http://localhost:8000/recipes", json=recipes_data)
if response.status_code == 200:
    result = response.json()
    print(f"Added {result['added_count']} recipes")
    print(f"Skipped {result['skipped_count']} recipes")
    print(f"Operation completed in {result['total_time_seconds']:.2f} seconds")
    print(f"Recipe IDs: {result['recipe_ids']}")

    # Display similarity information
    if result.get('sample_recipe_title'):
        print(f"\nSimilarity Analysis:")
        print(f"Sample recipe: {result['sample_recipe_title']} (ID: {result['sample_recipe_id']})")
        print(f"Most similar: {result['similar_recipe_title']} (ID: {result['similar_recipe_id']})")
        print(f"Similarity score: {result['similarity_score']:.3f}")
else:
    print(f"Failed to add recipes: {response.text}")
```

### cURL Example

```bash
curl -X POST "http://localhost:8000/recipes" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "id": "uuid-1",
      "title": "Chocolate Chip Cookies",
      "ingredients": ["flour", "butter", "sugar"],
      "instructions": ["Mix ingredients", "Bake"],
      "cuisine": "American"
    },
    {
      "id": "uuid-2",
      "title": "Pasta Carbonara",
      "ingredients": ["pasta", "eggs", "bacon"],
      "instructions": ["Cook pasta", "Mix with eggs"],
      "cuisine": "Italian"
    }
  ]'
```

### JavaScript Example

```javascript
// Add a single recipe
const recipeData = {
  title: "Chocolate Chip Cookies",
  description: "Classic homemade cookies",
  ingredients: ["2 cups flour", "1 cup butter", "1 cup sugar"],
  instructions: ["Preheat oven", "Mix ingredients", "Bake for 10 minutes"],
  cuisine: "American",
  total_time: 30,
};

fetch("http://localhost:8000/recipes", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify(recipeData),
})
  .then((response) => response.json())
  .then((data) => {
    console.log("Recipe added:", data.recipe_id);
  })
  .catch((error) => {
    console.error("Error:", error);
  });
```

## Feature Vector Calculation

The system automatically calculates feature vectors for new recipes using:

1. **TF-IDF Vectorizers** for text features:

   - Recipe titles
   - Ingredients
   - Instructions
   - Descriptions

2. **One-Hot Encoder** for categorical features:
   - Cuisine types

The feature vectors are:

- Stored in the database as JSON
- Used by the recommendation engine
- Compatible with existing recipes

## Validation and Similarity Checking

When a new recipe is added, the system automatically:

1. **Calculates Feature Vector**: Uses the same ML models as existing recipes
2. **Refreshes Recommendation Engine**: Updates the engine with the new recipe
3. **Finds Most Similar Recipe**: Uses cosine similarity to find the closest match
4. **Returns Validation Data**: Provides similarity score and similar recipe details

This validation helps confirm that:

- ✅ Feature vector calculation is working correctly
- ✅ The new recipe is properly integrated into the recommendation system
- ✅ Similarity matching is functioning as expected
- ✅ The recipe will be included in future recommendations

**Similarity Score Interpretation**:

- **0.9-1.0**: Very similar recipes (same cuisine, similar ingredients)
- **0.7-0.9**: Moderately similar recipes (same category, some shared ingredients)
- **0.5-0.7**: Somewhat similar recipes (same cuisine or category)
- **0.0-0.5**: Different recipes (different cuisines, ingredients, etc.)

## Database Operations

All database operations are centralized in the `DatabaseManager` class:

- **Recipe insertion**: `add_recipe()` method handles all database writes
- **Recipe retrieval**: `get_recipe()` method for single recipe lookup
- **Connection management**: Automatic connection handling and cleanup
- **Error handling**: Comprehensive error handling for database operations

## Elasticsearch Operations

All search operations are centralized in the `ElasticsearchService` class:

- **Recipe indexing**: `index_recipe()` method handles search indexing
- **Search functionality**: `search_recipes()` method for text-based search
- **Index management**: `create_index_if_not_exists()` for index setup
- **Connection management**: Automatic connection handling and error recovery

## Error Handling

The API provides comprehensive error handling:

- **Validation errors**: Invalid data format or missing required fields
- **ML model errors**: Issues with feature vector calculation
- **Database errors**: Connection or insertion problems (handled by DatabaseManager)
- **Elasticsearch errors**: Indexing issues (handled by ElasticsearchService, non-fatal)

## Integration with Existing System

New recipes are automatically integrated with:

1. **Recommendation Engine**: Feature vectors enable similarity-based recommendations
2. **Search Functionality**: Recipes are indexed in Elasticsearch for text search
3. **User Interactions**: Users can like, save, and provide feedback on new recipes
4. **Statistics**: New recipes are included in user stats and analytics

## Troubleshooting

### Common Issues

1. **ML Models Not Found**:

   ```
   Error: ML models not found. Please run the initialization script first
   ```

   **Solution**: Run `python init.py` in the `db_init` directory

2. **Database Connection Error**:

   ```
   Error: Failed to add recipe to database
   ```

   **Solution**: Check database connectivity and credentials

3. **Elasticsearch Connection Error**:
   ```
   Warning: Failed to index recipe in Elasticsearch
   ```
   **Solution**: Check Elasticsearch service status (non-fatal error)

### Debug Mode

Enable debug logging by setting the log level in `main.py`:

```python
setup_logging(level="DEBUG")
```

## Performance Considerations

- **Single recipe addition**: ~100-200ms (including feature vector calculation)
- **Memory usage**: ML models are loaded once and reused
- **Database efficiency**: Centralized connection management reduces overhead
- **Search efficiency**: Centralized Elasticsearch operations optimize indexing
- **Concurrent requests**: The service handles multiple simultaneous requests

## Security Notes

- Input validation prevents SQL injection
- Data sanitization ensures safe storage
- Error messages don't expose sensitive information
- Rate limiting can be added for production use

## Future Enhancements

Potential improvements:

- Recipe update/delete endpoints
- Feature vector recalculation for existing recipes
- ML model retraining with new data
- Recipe validation and quality scoring
- Bulk import from external sources (CSV, JSON files)
