"use client";

import { RecipeCard } from "@/components/recipe-card";
import { Recipe, RecommendationResponse, UserFeedbackResponse } from "@/types";
import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

export default function FYP() {
  const { data: session, status } = useSession();
  const [currentRecipe, setCurrentRecipe] = useState<Recipe | null>(null);
  const [loading, setLoading] = useState(true);
  const [recommendations, setRecommendations] = useState<Recipe[]>([]); // This array is treated as a queue
  const [swipedRecipeId, setSwipedRecipeId] = useState<string | null>(null); // Track the swiped recipe id instead of removing from the queue so that the animation can complete

  // Current recipe should always be the first non-swiped recipe in the recommendations array
  useEffect(() => {
    if (recommendations.length > 0) {
      const firstNonSwiped = recommendations.find(
        (recipe) => recipe.id !== swipedRecipeId,
      );
      setCurrentRecipe(firstNonSwiped || null);
    } else {
      setCurrentRecipe(null);
    }
  }, [recommendations, swipedRecipeId]);

  const fetchRecommendations = async () => {
    if (!session?.user?.id) {
      setLoading(false);
      return;
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const response = await fetch(
        `${apiUrl}/users/${session.user.id}/recommendations`,
      );

      if (response.ok) {
        const data: RecommendationResponse = await response.json();
        setRecommendations(data.recommendations);
        if (data.recommendations && data.recommendations.length > 0) {
          setCurrentRecipe(data.recommendations[0]);
        } else {
          setCurrentRecipe(null);
        }
      } else {
        toast.error("Error", {
          description: "Failed to load recommendations",
        });
      }
    } catch (error) {
      toast.error("Error", {
        description: "Failed to load recommendations",
      });
    } finally {
      setLoading(false);
    }
  };

  const submitFeedback = async (
    recipeId: string,
    feedbackType: "like" | "dislike",
  ) => {
    if (!session?.user?.id) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const response = await fetch(
        `${apiUrl}/users/${session.user.id}/feedback`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            recipe_id: recipeId,
            feedback_type: feedbackType,
          }),
        },
      );

      if (!response.ok) {
        throw new Error("Failed to submit feedback");
      }

      // Add the new recipe to the end of the recommendations array
      const data: UserFeedbackResponse = await response.json();
      setRecommendations((prev) => {
        return [...prev, data.next_recommendation];
      });
    } catch (error) {
      toast.error("Error", {
        description: "Failed to submit feedback",
      });
    }
  };

  const handleSwipe = async (swipe: "like" | "dislike") => {
    if (!currentRecipe) return;

    // Capture the recipe ID and title before any state changes
    const recipeId = currentRecipe.id;
    const recipeTitle = currentRecipe.title;

    // Mark the recipe as swiped to hide it from the current recipe selection
    setSwipedRecipeId(recipeId);

    // Show toast immediately for better UX
    if (swipe === "like") {
      toast("Recipe liked!", {
        description: `${recipeTitle} added to your likes`,
      });
    }

    // Submit feedback to backend in the background
    try {
      await submitFeedback(recipeId, swipe);
      // Remove the recipe from the array after backend submission
      setRecommendations((prev) => {
        return prev.filter((recipe) => recipe.id !== recipeId);
      });
      // Clear the swiped recipe ID
      setSwipedRecipeId(null);
    } catch (error) {
      toast.error("Error", {
        description: "Failed to submit feedback",
      });
      // If backend submission fails, unmark the recipe as swiped
      setSwipedRecipeId(null);
    }
  };

  const handleBookmark = async () => {
    if (!currentRecipe) return;

    try {
      // For now, just show a toast. You might want to implement bookmarking later
      toast("Recipe bookmarked!", {
        description: `${currentRecipe.title} saved to your collection`,
      });
    } catch (error) {
      toast.error("Error", {
        description: "Failed to bookmark recipe",
      });
    }
  };

  useEffect(() => {
    if (status === "authenticated" && session?.user?.id) {
      fetchRecommendations();
    } else if (
      (status === "authenticated" && !session?.user?.id) ||
      status === "unauthenticated"
    ) {
      setLoading(false);
    }
  }, [session, status]);

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center pt-16">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-orange-500"></div>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return (
      <div className="flex min-h-screen items-center justify-center px-4 pt-16">
        <div className="text-center">
          <h2 className="mb-2 text-2xl font-bold text-gray-800">
            Please log in
          </h2>
          <p className="text-gray-600">
            You need to be logged in to view recommendations.
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center pt-16">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-orange-500"></div>
      </div>
    );
  }

  if (!currentRecipe) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4 pt-16">
        <div className="text-center">
          <h2 className="mb-2 text-2xl font-bold text-gray-800">
            No more recipes!
          </h2>
          <p className="text-gray-600">
            You've seen all available recipes. Check back later for more!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 pt-8 pb-28">
      <RecipeCard
        recipe={currentRecipe}
        onSwipe={handleSwipe}
        onBookmark={handleBookmark}
      />
    </div>
  );
}
