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
