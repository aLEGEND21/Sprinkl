# main.py - FastAPI application for recipe recommendations
import logging
import random
import time
from datetime import datetime
from typing import List, Optional

from database import DatabaseManager
from dotenv import load_dotenv
from es_service import ElasticsearchService
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from logging_config import setup_logging
from models import (
    Recipe,
    RecipeBatchCreateResponse,
    RecipeCreateRequest,
    RecommendationResponse,
    UserFeedbackRequest,
    UserFeedbackResponse,
    UserLoginRequest,
    UserLoginResponse,
    UserStatsResponse,
)
from recipe_service import RecipeService

# Load environment variables
load_dotenv()

# Configure logging
setup_logging(level="INFO")
logger = logging.getLogger(__name__)


# Initialize FastAPI app
app = FastAPI(
    title="Food Recommendation API",
    description="AI-powered food recommendation system",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database manager
db_manager = DatabaseManager()

# Initialize Elasticsearch service
try:
    es_service = ElasticsearchService(db_manager)
    logger.info("Elasticsearch service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Elasticsearch service: {e}")
    es_service = None

# Initialize Recipe service
try:
    recipe_service = RecipeService(db_manager, es_service)
    logger.info("Recipe service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Recipe service: {e}")
    recipe_service = None


# Database dependency
def get_db():
    return db_manager


# Elasticsearch dependency
def get_es_service():
    if es_service is None:
        raise HTTPException(
            status_code=503, detail="Elasticsearch service is not available"
        )
    return es_service


# Recipe service dependency
def get_recipe_service():
    if recipe_service is None:
        raise HTTPException(status_code=503, detail="Recipe service is not available")
    return recipe_service


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Food Recommendation API is running!", "status": "healthy"}


@app.get("/reset")
async def reset_database(db: DatabaseManager = Depends(get_db)):
    """Reset database tables - clears users, user_feedback, and recommendations tables"""
    try:
        logger.info("Resetting database tables...")

        conn = db.get_connection()
        cursor = conn.cursor()

        # Clear tables in the correct order to respect foreign key constraints
        # Start with tables that reference others
        cursor.execute("DELETE FROM recommendations")
        logger.info("Cleared recommendations table")

        cursor.execute("DELETE FROM user_feedback")
        logger.info("Cleared user_feedback table")

        cursor.execute("DELETE FROM users")
        logger.info("Cleared users table")

        conn.commit()
        cursor.close()
        conn.close()

        logger.info("Database reset completed successfully")
        return {
            "message": "Database reset successful",
            "tables_cleared": ["recommendations", "user_feedback", "users"],
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to reset database: {str(e)}"
        )


@app.get("/counts")
async def get_table_counts(db: DatabaseManager = Depends(get_db)):
    """Get row counts for all tables in the database"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        counts = {}

        # Get count for each table
        tables = ["recipes", "users", "user_feedback", "recommendations"]

        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as total FROM {table}")
            result = cursor.fetchone()
            if result and ("total" in result):
                count = result["total"]
            else:
                count = 0
            counts[table] = count

        cursor.close()
        conn.close()

        return {
            "table_counts": counts,
            "total_records": sum(counts.values()),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting table counts: {str(e)} (type: {type(e)})")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get table counts: {str(e)} (type: {type(e)})",
        )


@app.post("/api/users/login", response_model=UserLoginResponse)
async def user_login(
    login_data: UserLoginRequest, db: DatabaseManager = Depends(get_db)
):
    """Add the user to the database if they don't exist and load their initial recommendations."""
    print(f"Login data: {login_data}")
    # Create the user account in the database
    db.create_user_if_not_exists(
        user_id=login_data.user_id,
        email=login_data.email,
        name=login_data.name,
        image_url=login_data.image,
    )

    return UserLoginResponse(
        user_id=login_data.user_id,
        email=login_data.email,
        name=login_data.name,
        message="Login successful",
    )


@app.post("/users/{user_id}/feedback", response_model=UserFeedbackResponse)
async def submit_feedback(
    user_id: str,
    feedback: UserFeedbackRequest,
    db: DatabaseManager = Depends(get_db),
    es_service: ElasticsearchService = Depends(get_es_service),
):
    """Submit user feedback (like/dislike) for a recipe"""

    # Validate feedback type
    if feedback.feedback_type not in ["like", "dislike"]:
        raise HTTPException(
            status_code=400, detail="Feedback type must be 'like' or 'dislike'"
        )

    # Submit feedback and remove the recommendation from the list
    success = db.save_feedback(user_id, feedback.recipe_id, feedback.feedback_type)
    db.remove_recommendation(user_id, feedback.recipe_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to submit feedback")

    # Get the next recommendation for the user
    user_feedback = db.get_feedback(user_id)
    prev_recs = db.get_recommendations(user_id)
    rec_ids = es_service.generate_recommendations(
        user_feedback, prev_recs, num_recommendations=1
    )
    rec_id = rec_ids[0]
    db.save_recommendations(user_id, [rec_id])
    next_rec = db.get_recipe(rec_id)

    return UserFeedbackResponse(
        message="Feedback submitted successfully",
        user_id=user_id,
        recipe_id=feedback.recipe_id,
        feedback_type=feedback.feedback_type,
        next_recommendation=next_rec,
    )


@app.get("/users/{user_id}/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: str,
    num_recommendations: Optional[int] = 10,
    db: DatabaseManager = Depends(get_db),
    es: ElasticsearchService = Depends(get_es_service),
):
    """Get personalized recipe recommendations for a user using Elasticsearch feature vector similarity"""
    # Load the saved recommendations from the database
    rec_ids = db.get_recommendations(user_id)

    # If no saved recommendations, generate new ones using Elasticsearch
    if not rec_ids:
        user_feedback = db.get_feedback(user_id)
        prev_recs = []

        # Use Elasticsearch service for recommendations
        rec_ids = es.generate_recommendations(
            user_feedback, prev_recs, num_recommendations=num_recommendations
        )

        db.save_recommendations(user_id, rec_ids)

    # Load the full recipe data in bulk
    recs = db.get_multiple_recipes(rec_ids)

    return RecommendationResponse(
        user_id=user_id,
        recommendations=recs,
        last_updated=datetime.now().isoformat(),
        total_recommendations=len(recs),
    )


@app.get("/recipes/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: str, db: DatabaseManager = Depends(get_db)):
    """Get details for a specific recipe"""
    recipe = db.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return recipe


@app.get("/search")
async def search_recipes(
    q: str,
    page: int = 1,
    size: int = 10,
    fuzziness: str = "AUTO",
    db: DatabaseManager = Depends(get_db),
    es: ElasticsearchService = Depends(get_es_service),
):
    """Search recipes by title using GET request (easier for testing)"""
    logger.info(f"Searching for recipes with query: {q}")

    # Validate pagination parameters
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be greater than 0")
    if size < 1 or size > 100:
        raise HTTPException(status_code=400, detail="Size must be between 1 and 100")

    # Validate fuzziness parameter
    valid_fuzziness = ["AUTO", "0", "1", "2"]
    if fuzziness not in valid_fuzziness:
        raise HTTPException(
            status_code=400, detail=f"Fuzziness must be one of: {valid_fuzziness}"
        )

    # Search in Elasticsearch
    search_results = es.search_recipes(
        query=q, page=page, size=size, fuzziness=fuzziness
    )

    if not search_results:
        return {
            "query": q,
            "results": [],
            "total_hits": 0,
            "page": page,
            "size": size,
            "total_pages": 0,
            "has_next": False,
            "has_previous": False,
        }

    # Get full recipe data from database in bulk
    recipes = db.get_multiple_recipes(search_results["recipe_ids"])

    return {
        "query": q,
        "results": recipes,
        "total_hits": search_results["total_hits"],
        "page": search_results["page"],
        "size": search_results["size"],
        "total_pages": search_results["total_pages"],
        "has_next": search_results["has_next"],
        "has_previous": search_results["has_previous"],
    }


@app.get("/users/{user_id}/saved-recipes")
async def get_saved_recipes(user_id: str, db: DatabaseManager = Depends(get_db)):
    """Get all saved recipes for a user"""
    saved_recipe_ids = db.get_saved_recipes(user_id)

    # Get full recipe data for saved recipes in bulk
    saved_recipes = db.get_multiple_recipes(saved_recipe_ids)

    return {
        "user_id": user_id,
        "saved_recipes": saved_recipes,
        "total_saved": len(saved_recipes),
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/users/{user_id}/saved-recipes/{recipe_id}")
async def save_recipe(
    user_id: str, recipe_id: str, db: DatabaseManager = Depends(get_db)
):
    """Save a recipe for a user"""
    # Verify the recipe exists
    recipe = db.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Save the recipe
    success = db.save_recipe(user_id, recipe_id)

    return {
        "user_id": user_id,
        "recipe_id": recipe_id,
        "saved": success,
        "message": "Recipe saved successfully" if success else "Recipe already saved",
        "timestamp": datetime.now().isoformat(),
    }


@app.delete("/users/{user_id}/saved-recipes/{recipe_id}")
async def unsave_recipe(
    user_id: str, recipe_id: str, db: DatabaseManager = Depends(get_db)
):
    """Remove a saved recipe for a user"""
    # Remove the saved recipe
    success = db.unsave_recipe(user_id, recipe_id)

    return {
        "user_id": user_id,
        "recipe_id": recipe_id,
        "removed": success,
        "message": "Recipe removed from saved recipes"
        if success
        else "Recipe was not saved",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/users/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(user_id: str, db: DatabaseManager = Depends(get_db)):
    """Get user stats: number of liked, saved, viewed recipes, and favorite cuisine."""
    feedback = db.get_feedback(user_id)
    liked = feedback.get("liked", [])
    disliked = feedback.get("disliked", [])
    num_liked = len(liked)
    num_viewed = len(liked) + len(disliked)
    saved = db.get_saved_recipes(user_id)
    num_saved = len(saved)

    # Favorite cuisine from liked recipes
    favorite_cuisine = None
    if liked:
        liked_recipes = db.get_multiple_recipes(liked)
        cuisine_counts = {}
        for recipe in liked_recipes:
            cuisine = getattr(recipe, "cuisine", None)
            if cuisine:
                cuisine_counts[cuisine] = cuisine_counts.get(cuisine, 0) + 1
        if cuisine_counts:
            favorite_cuisine = max(cuisine_counts.items(), key=lambda x: x[1])[0]

    return UserStatsResponse(
        user_id=user_id,
        num_liked=num_liked,
        num_saved=num_saved,
        num_viewed=num_viewed,
        favorite_cuisine=favorite_cuisine,
    )


@app.delete("/users/{user_id}")
async def delete_user(user_id: str, db: DatabaseManager = Depends(get_db)):
    """Delete a user and all their related data."""
    success = db.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=404, detail="User not found or could not be deleted"
        )
    return {"message": "User deleted successfully", "user_id": user_id}


@app.post("/recipes", response_model=RecipeBatchCreateResponse)
async def create_recipes(
    recipes_data: List[RecipeCreateRequest],
    recipe_svc: RecipeService = Depends(get_recipe_service),
    db: DatabaseManager = Depends(get_db),
):
    """
    Create multiple recipes with automatic feature vector calculation and Elasticsearch indexing.

    This endpoint:
    1. Adds recipes to the database
    2. Generates feature vectors using TF-IDF and PCA
    3. Indexes recipes in Elasticsearch with feature vectors
    4. Makes recipes immediately available for similarity searches

    The feature vectors enable the recipe to be included in cosine similarity queries
    for personalized recommendations.
    """
    start_time = time.time()
    recipe_dicts = [recipe.dict() for recipe in recipes_data]
    recipe_ids = recipe_svc.add_recipe(recipe_dicts)
    end_time = time.time()

    # Randomly select one of the added recipes for similarity analysis
    sample_recipe_id = None
    sample_recipe_title = None
    similar_recipe_id = None
    similar_recipe_title = None
    similarity_score = None

    if recipe_ids:
        # Randomly select one of the successfully added recipes
        sample_recipe_id = random.choice(recipe_ids)

        # Get the recipe details
        sample_recipe = db.get_recipe(sample_recipe_id)
        if sample_recipe:
            sample_recipe_title = sample_recipe.title

            # Find the most similar recipe (excluding itself)
            similar_recipe_info = recipe_svc.get_most_similar_recipe(sample_recipe_id)
            if similar_recipe_info and similar_recipe_info.get("similar_recipe"):
                similar_recipe = similar_recipe_info["similar_recipe"]
                similar_recipe_id = similar_recipe.id
                similar_recipe_title = similar_recipe.title
                similarity_score = similar_recipe_info.get("similarity_score")

    return RecipeBatchCreateResponse(
        message=f"Successfully processed {len(recipes_data)} recipes",
        added_count=len(recipe_ids),
        skipped_count=len(recipes_data) - len(recipe_ids),
        recipe_ids=recipe_ids,
        sample_recipe_id=sample_recipe_id,
        sample_recipe_title=sample_recipe_title,
        similar_recipe_id=similar_recipe_id,
        similar_recipe_title=similar_recipe_title,
        similarity_score=similarity_score,
        total_time_seconds=round(end_time - start_time, 2),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
