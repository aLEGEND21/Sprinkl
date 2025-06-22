# main.py - FastAPI application for recipe recommendations
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from datetime import datetime
import logging
from recommendation_engine import RecommendationEngine
from database import DatabaseManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
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


# Pydantic models for request/response
class UserLoginRequest(BaseModel):
    user_id: str
    email: str
    name: str
    image: Optional[str] = None


class UserLoginResponse(BaseModel):
    user_id: str
    email: str
    name: str
    is_new_user: bool
    message: str
    created_at: str


class UserFeedbackRequest(BaseModel):
    user_id: str
    recipe_id: str
    feedback_type: str  # 'like' or 'dislike'


class RecommendationRequest(BaseModel):
    user_id: str
    num_recommendations: Optional[int] = 10
    cuisine_filter: Optional[str] = None
    max_time_mins: Optional[int] = None


class Recipe(BaseModel):
    id: str
    recipe_name: str
    cuisine: Optional[str]
    time_mins: Optional[int]
    ingredient_count: Optional[int]
    ingredient_list: Optional[List[str]]
    instructions: Optional[str]
    recipe_url: Optional[str]
    image_url: Optional[str]


class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: List[Recipe]
    last_updated: str
    total_recommendations: int


class UserStats(BaseModel):
    user_id: str
    total_likes: int
    total_dislikes: int
    favorite_cuisines: List[Dict[str, Any]]
    avg_cooking_time: Optional[float]


# Database dependency
def get_db():
    return DatabaseManager()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Food Recommendation API is running!", "status": "healthy"}


@app.post("/api/users/login", response_model=UserLoginResponse)
async def user_login(login_data: UserLoginRequest, db: DatabaseManager = Depends(get_db)):
    """Handle user login and add user to database if they don't exist"""
    try:
        logger.info(f"Processing login for user: {login_data.user_id}")
        
        # Check if user already exists
        existing_user = await db.get_user_by_id(login_data.user_id)
        is_new_user = existing_user is None
        
        if is_new_user:
            # Create new user
            logger.info(f"Creating new user: {login_data.user_id}")
            success = await db.create_user(
                user_id=login_data.user_id,
                email=login_data.email,
                name=login_data.name,
                image_url=login_data.image,
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create user in database")
            
            # Generate initial recommendations for new user
            try:
                await recommendation_engine.generate_fresh_recommendations(login_data.user_id, db)
                logger.info(f"Generated initial recommendations for new user: {login_data.user_id}")
            except Exception as e:
                logger.warning(f"Failed to generate initial recommendations for user {login_data.user_id}: {str(e)}")
                # Don't fail the login if recommendation generation fails
        else:
            # Update existing user information
            logger.info(f"Updating existing user: {login_data.user_id}")
            success = await db.update_user(
                user_id=login_data.user_id,
                email=login_data.email,
                name=login_data.name,
                image_url=login_data.image,
            )
            
            if not success:
                logger.warning(f"Failed to update user {login_data.user_id}, but continuing with login")
        
        # Log successful login
        logger.info(f"User login successful: {login_data.user_id} (new user: {is_new_user})")
        
        return UserLoginResponse(
            user_id=login_data.user_id,
            email=login_data.email,
            name=login_data.name,
            is_new_user=is_new_user,
            message="Login successful" if not is_new_user else "User created and login successful",
            created_at=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing user login: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/users/{user_id}/feedback", response_model=dict)
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

        # Ensure user exists
        await db.ensure_user_exists(user_id)

        # Submit feedback
        success = await db.submit_feedback(
            user_id, feedback.recipe_id, feedback.feedback_type
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to submit feedback")

        # Trigger recommendation update
        await recommendation_engine.update_user_recommendations(user_id, db)

        return {
            "message": "Feedback submitted successfully",
            "user_id": user_id,
            "recipe_id": feedback.recipe_id,
            "feedback_type": feedback.feedback_type,
        }

    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/users/{user_id}/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: str,
    num_recommendations: Optional[int] = 10,
    cuisine_filter: Optional[str] = None,
    max_time_mins: Optional[int] = None,
    db: DatabaseManager = Depends(get_db),
):
    """Get personalized recipe recommendations for a user"""
    try:
        # Ensure user exists
        await db.ensure_user_exists(user_id)

        # Get recommendations from database or generate new ones
        recommendations = await recommendation_engine.get_recommendations(
            user_id, db, num_recommendations, cuisine_filter, max_time_mins
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


@app.get("/users/{user_id}/stats", response_model=UserStats)
async def get_user_stats(user_id: str, db: DatabaseManager = Depends(get_db)):
    """Get user statistics and preferences"""
    try:
        stats = await db.get_user_stats(user_id)
        return stats

    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
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
    max_time_mins: Optional[int] = None,
    limit: Optional[int] = 20,
    db: DatabaseManager = Depends(get_db),
):
    """Search recipes with optional filters"""
    try:
        recipes = await db.search_recipes(query, cuisine, max_time_mins, limit)
        return recipes

    except Exception as e:
        logger.error(f"Error searching recipes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/users/{user_id}/recommendations/refresh")
async def refresh_recommendations(user_id: str, db: DatabaseManager = Depends(get_db)):
    """Manually refresh recommendations for a user"""
    try:
        # Ensure user exists
        await db.ensure_user_exists(user_id)

        # Force refresh recommendations
        recommendations = await recommendation_engine.generate_fresh_recommendations(
            user_id, db
        )

        return {
            "message": "Recommendations refreshed successfully",
            "user_id": user_id,
            "new_recommendations_count": len(recommendations),
        }

    except Exception as e:
        logger.error(f"Error refreshing recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3009)
