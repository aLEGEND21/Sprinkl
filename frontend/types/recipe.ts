// types/recipe.ts - Recipe type definitions for the FoodApp frontend

export interface Recipe {
  id: string;
  title: string;
  description?: string;
  recipe_url?: string;
  image_url?: string;
  ingredients: string[];
  instructions: string[];
  category?: string;
  cuisine?: string;
  site_name?: string;
  keywords: string[];
  dietary_restrictions: string[];
  total_time?: number;
  overall_rating?: number;
}

export interface RecipeCardProps {
  recipe: Recipe;
  onSwipe: (swipe: "like" | "dislike") => void;
  onBookmark: () => void;
}

export interface UserFeedbackRequest {
  recipe_id: string;
  feedback_type: "like" | "dislike";
}

export interface UserFeedbackResponse {
  message: string;
  user_id: string;
  recipe_id: string;
  feedback_type: "like" | "dislike";
  next_recommendation: Recipe;
}

export interface RecommendationResponse {
  user_id: string;
  recommendations: Recipe[];
  last_updated: string;
  total_recommendations: number;
}
