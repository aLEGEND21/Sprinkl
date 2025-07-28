# models.py - Pydantic models and type definitions for the Food Recommendation API
from typing import List, Literal, Optional

from pydantic import BaseModel


class Recipe(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    recipe_url: Optional[str] = None
    image_url: Optional[str] = None
    ingredients: List[str]
    instructions: List[str]
    category: Optional[str] = None
    cuisine: Optional[str] = None
    site_name: Optional[str] = None
    keywords: List[str] = []
    dietary_restrictions: List[str] = []
    total_time: Optional[int] = None
    overall_rating: Optional[float] = None


class RecipeSummary(BaseModel):
    """Simplified recipe model with only essential fields"""

    id: str
    title: str


class RecipeCreateRequest(BaseModel):
    """Model for creating a new recipe"""

    id: str
    title: str
    description: Optional[str] = None
    recipe_url: Optional[str] = None
    image_url: Optional[str] = None
    ingredients: List[str]
    instructions: List[str]
    category: Optional[str] = None
    cuisine: Optional[str] = None
    site_name: Optional[str] = None
    keywords: List[str] = []
    dietary_restrictions: List[str] = []
    total_time: Optional[int] = None
    overall_rating: Optional[float] = None


class RecipeBatchCreateRequest(BaseModel):
    """Model for creating multiple recipes"""

    recipes: List[RecipeCreateRequest]


class RecipeBatchCreateResponse(BaseModel):
    """Response model for batch recipe creation"""

    message: str
    added_count: int
    skipped_count: int
    recipe_ids: List[str]
    errors: List[str] = []
    # Similarity information for a randomly selected recipe
    sample_recipe_id: Optional[str] = None
    sample_recipe_title: Optional[str] = None
    similar_recipe_id: Optional[str] = None
    similar_recipe_title: Optional[str] = None
    similarity_score: Optional[float] = None
    # Performance metrics
    total_time_seconds: float


class SearchResponse(BaseModel):
    query: str
    results: List[Recipe]
    total_hits: int
    page: int
    size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class UserLoginRequest(BaseModel):
    user_id: str
    email: str
    name: str
    image: Optional[str] = None


class UserLoginResponse(BaseModel):
    user_id: str
    email: str
    name: str
    message: str


class UserFeedbackRequest(BaseModel):
    recipe_id: str
    feedback_type: Literal["like", "dislike"]


class UserFeedbackResponse(BaseModel):
    message: str
    user_id: str
    recipe_id: str
    feedback_type: Literal["like", "dislike"]
    next_recommendation: Recipe
    next_recommendation: Recipe
    next_recommendation: Recipe


class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: List[Recipe]
    last_updated: str
    total_recommendations: int


class UserStatsResponse(BaseModel):
    user_id: str
    num_liked: int
    num_saved: int
    num_viewed: int
    favorite_cuisine: Optional[str] = None
