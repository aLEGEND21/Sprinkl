# main.py - FastAPI application for recipe recommendations
import logging
from datetime import datetime
from typing import Optional

from database import DatabaseManager
from dotenv import load_dotenv
from elasticsearch_service import ElasticsearchService
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from logging_config import setup_logging
from models import (
    Recipe,
    RecommendationResponse,
    UserFeedbackRequest,
    UserFeedbackResponse,
    UserLoginRequest,
    UserLoginResponse,
)
from rec_engine import RecommendationEngine

# Load environment variables
load_dotenv()

# Configure logging
setup_logging()
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

# Initialize recommendation engine
recommendation_engine = RecommendationEngine(DatabaseManager())

# Initialize Elasticsearch service
try:
    es_service = ElasticsearchService()
    logger.info("Elasticsearch service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Elasticsearch service: {e}")
    es_service = None


# Database dependency
def get_db():
    return DatabaseManager()


# Elasticsearch dependency
def get_es_service():
    if es_service is None:
        raise HTTPException(
            status_code=503, detail="Elasticsearch service is not available"
        )
    return es_service


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
    user_id: str, feedback: UserFeedbackRequest, db: DatabaseManager = Depends(get_db)
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
    rec_ids = recommendation_engine.generate_recommendations(
        user_feedback, prev_recs, num_recommendations=1
    )
    rec_id = rec_ids[0]
    db.save_recommendations(user_id, [rec_id])
    next_rec = db.get_recipe_data(rec_id)

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
):
    """Get personalized recipe recommendations for a user"""
    # Load the saved recommendations from the database
    rec_ids = db.get_recommendations(user_id)

    # If no saved recommendations, generate new ones
    if not rec_ids:
        user_feedback = db.get_feedback(user_id)
        prev_recs = []
        rec_ids = recommendation_engine.generate_recommendations(
            user_feedback, prev_recs, num_recommendations=num_recommendations
        )
        db.save_recommendations(user_id, rec_ids)

    # Load the full recipe data
    recs = []
    for rec_id in rec_ids:
        recs.append(db.get_recipe_data(rec_id))

    return RecommendationResponse(
        user_id=user_id,
        recommendations=recs,
        last_updated=datetime.now().isoformat(),
        total_recommendations=len(recs),
    )


@app.get("/recipes/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: str, db: DatabaseManager = Depends(get_db)):
    """Get details for a specific recipe"""
    recipe = db.get_recipe_data(recipe_id)
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
    print(f"Searching for recipes with query: {q}")
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

    # Get full recipe data from database
    recipes = []
    for recipe_id in search_results["recipe_ids"]:
        recipe = db.get_recipe_data(recipe_id)
        if recipe:
            recipes.append(recipe)

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

    # Get full recipe data for each saved recipe
    saved_recipes = []
    for recipe_id in saved_recipe_ids:
        recipe = db.get_recipe_data(recipe_id)
        saved_recipes.append(recipe)

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
    recipe = db.get_recipe_data(recipe_id)
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
