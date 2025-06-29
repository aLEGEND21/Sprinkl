# main.py - FastAPI application for recipe recommendations
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from dotenv import load_dotenv
from datetime import datetime
import logging
import sys
from recommendation_engine import RecommendationEngine
from database import DatabaseManager
from models import (
    UserLoginRequest,
    UserLoginResponse,
    UserFeedbackRequest,
    UserFeedbackResponse,
    Recipe,
    RecommendationResponse,
)
import json

# Load environment variables
load_dotenv()

# Configure logging to avoid duplicates
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(name)s: %(message)s",
)

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
recommendation_engine = RecommendationEngine()


# Database dependency
def get_db():
    return DatabaseManager()


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
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            counts[table] = count

        cursor.close()
        conn.close()

        return {
            "table_counts": counts,
            "total_records": sum(counts.values()),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting table counts: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get table counts: {str(e)}"
        )


@app.post("/api/users/login", response_model=UserLoginResponse)
async def user_login(
    login_data: UserLoginRequest, db: DatabaseManager = Depends(get_db)
):
    """Add the user to the database if they don't exist and load their initial recommendations."""

    # Create the user account in the database
    await db.create_user_if_not_exists(
        user_id=login_data.user_id,
        email=login_data.email,
        name=login_data.name,
        image_url=login_data.image,
    )

    # Load the user's initial recommendations
    recs = await recommendation_engine.get_recommendations(login_data.user_id, db)
    await db.save_recommendations(login_data.user_id, recs)

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
    try:
        # Validate feedback type
        if feedback.feedback_type not in ["like", "dislike"]:
            raise HTTPException(
                status_code=400, detail="Feedback type must be 'like' or 'dislike'"
            )

        # Submit feedback
        success = await db.submit_feedback(
            user_id, feedback.recipe_id, feedback.feedback_type
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to submit feedback")

        # Get the next recommendation for the user
        rec_ids = await recommendation_engine.get_recommendations(
            user_id, db, num_recommendations=1
        )
        await db.save_recommendations(user_id, rec_ids)
        next_rec = await db.get_recipe_by_id(rec_ids[0])

        print(
            "Next recommendation: \n",
            json.dumps(
                next_rec.dict() if hasattr(next_rec, "dict") else next_rec, indent=4
            ),
        )

        return UserFeedbackResponse(
            message="Feedback submitted successfully",
            user_id=user_id,
            recipe_id=feedback.recipe_id,
            feedback_type=feedback.feedback_type,
            next_recommendation=Recipe(**next_rec),
        )

    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/users/{user_id}/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: str,
    num_recommendations: Optional[int] = 10,
    db: DatabaseManager = Depends(get_db),
):
    """Get personalized recipe recommendations for a user"""
    try:
        # Get recommendations from database or generate new ones
        recommendations = await recommendation_engine.get_recommendations(
            user_id,
            db,
            num_recommendations,
        )

        # Load the recipes from the database
        recommendations = await db.get_recipes_by_ids(recommendations)
        recommendations = [Recipe(**rec) for rec in recommendations]

        print(
            "InitialRecommendations: \n",
            json.dumps(
                [
                    rec.dict() if hasattr(rec, "dict") else rec
                    for rec in recommendations
                ],
                indent=4,
            ),
        )

        return RecommendationResponse(
            user_id=user_id,
            recommendations=recommendations,
            last_updated=datetime.now().isoformat(),
            total_recommendations=len(recommendations),
        )

    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/recipes/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: str, db: DatabaseManager = Depends(get_db)):
    """Get details for a specific recipe"""
    try:
        recipe = await db.get_recipe_by_id(recipe_id)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        return recipe

    except Exception as e:
        logger.error(f"Error getting recipe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/recipes", response_model=List[Recipe])
async def search_recipes(
    query: Optional[str] = None,
    cuisine: Optional[str] = None,
    max_time: Optional[int] = None,
    limit: Optional[int] = 20,
    db: DatabaseManager = Depends(get_db),
):
    """Search recipes with optional filters"""
    try:
        recipes = await db.search_recipes(query, cuisine, max_time, limit)
        return recipes

    except Exception as e:
        logger.error(f"Error searching recipes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
