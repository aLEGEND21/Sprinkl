# main.py - FastAPI application for recipe recommendations
import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from database import DatabaseManager
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import (
    Recipe,
    RecommendationResponse,
    UserFeedbackRequest,
    UserFeedbackResponse,
    UserLoginRequest,
    UserLoginResponse,
)
from recommendation_engine import RecommendationEngine

# Load environment variables
load_dotenv()


# --- Logging Configuration ---
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[37m",  # White
        logging.INFO: "\033[94m",  # Blue
        logging.WARNING: "\033[93m",  # Yellow
        logging.ERROR: "\033[91m",  # Red
        logging.CRITICAL: "\033[1;91m",  # Bold Red
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(levelname)s %(asctime)s [%(name)s]: %(message)s"

# Remove all handlers associated with the root logger object to avoid duplicate logs
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

if os.getenv("ENV", "development") == "development":
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter(LOG_FORMAT))
else:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

logging.basicConfig(
    level=LOG_LEVEL,
    handlers=[handler],
    force=True,
)

logger = logging.getLogger(__name__)

# --- End Logging Configuration ---


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

        # Convert recipe data to be JSON serializable
        if hasattr(next_rec, "dict"):
            recipe_data = next_rec.dict()
        else:
            recipe_data = next_rec

        # Convert any Decimal objects to regular numbers
        recipe_data = convert_decimals(recipe_data)

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
        # Load the saved recommendations from the database
        recommendation_ids = await db.get_saved_recommendations(
            user_id, num_recommendations
        )

        if not recommendation_ids:
            # If no saved recommendations, generate new ones
            recommendation_ids = await recommendation_engine.get_recommendations(
                user_id, db, num_recommendations
            )
            # Save the new recommendations
            await db.save_recommendations(user_id, recommendation_ids)

        # Load the full recipe data
        recommendations = await db.get_recipes_by_ids(recommendation_ids)
        recommendations = [Recipe(**rec) for rec in recommendations]

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


def convert_decimals(obj):
    """Convert Decimal objects to regular numbers for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    else:
        return obj


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
