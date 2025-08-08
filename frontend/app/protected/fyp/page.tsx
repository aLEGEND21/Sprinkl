"use client";

import { FYPRecipeCard } from "@/components/fyp-recipe-card";
import { RecipeImage } from "@/components/ui/recipe-image";
import { Recipe, RecommendationResponse, UserFeedbackResponse } from "@/types";
import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

export default function FYP() {
  const { data: session } = useSession();
  const [loading, setLoading] = useState(true);
  const [currentRecipe, setCurrentRecipe] = useState<Recipe | null>(null);
  const [recommendations, setRecommendations] = useState<Recipe[]>([]); // This array is treated as a queue
  const [savedRecipeIds, setSavedRecipeIds] = useState<Set<string>>(new Set());

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
        throw new Error("Failed to load recommendations");
      }
    } catch (error) {
      toast.error("Failed to load recommendations");
    } finally {
      setLoading(false);
    }
  };

  const fetchSavedRecipes = async () => {
    if (!session?.user?.id) return;

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const response = await fetch(
        `${apiUrl}/users/${session.user.id}/saved-recipes`,
      );

      if (response.ok) {
        const data = await response.json();
        const savedIds = new Set<string>(
          data.saved_recipes.map((recipe: Recipe) => recipe.id as string),
        );
        setSavedRecipeIds(savedIds);
      } else {
        console.error("Failed to load saved recipes");
      }
    } catch (error) {
      console.error("Error loading saved recipes:", error);
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
      toast.error("Failed to submit feedback");
    }
  };

  const handleSwipe = async (swipe: "like" | "dislike") => {
    if (!currentRecipe) return;

    // Submit feedback to backend in the background
    try {
      await submitFeedback(currentRecipe.id, swipe);
    } catch (error) {
      toast.error("Error", {
        description: "Failed to submit feedback",
      });
    }
  };

  const handleBookmark = async () => {
    if (!currentRecipe || !session?.user?.id) return;

    const isCurrentlySaved = savedRecipeIds.has(currentRecipe.id);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;

    try {
      if (isCurrentlySaved) {
        // Unsave the recipe
        const response = await fetch(
          `${apiUrl}/users/${session.user.id}/saved-recipes/${currentRecipe.id}`,
          {
            method: "DELETE",
          },
        );

        if (response.ok) {
          setSavedRecipeIds((prev) => {
            const newSet = new Set(prev);
            newSet.delete(currentRecipe.id);
            return newSet;
          });
        } else {
          throw new Error("Failed to unsave recipe");
        }
      } else {
        // Save the recipe
        const response = await fetch(
          `${apiUrl}/users/${session.user.id}/saved-recipes/${currentRecipe.id}`,
          {
            method: "POST",
          },
        );

        if (response.ok) {
          setSavedRecipeIds((prev) => new Set([...prev, currentRecipe.id]));
        } else {
          throw new Error("Failed to save recipe");
        }
      }
    } catch (error) {
      toast.error(`Failed to ${isCurrentlySaved ? "unsave" : "save"} recipe`);
    }
  };

  // Pass a seperate function to the Recipe Card to handle the next recipe because it must be called after the
  // animation completes
  const handleNextRecipe = (latest: "like" | "dislike") => {
    setRecommendations((prev) => {
      return prev.filter((recipe) => recipe.id !== currentRecipe?.id);
    });
  };

  useEffect(() => {
    if (session?.user?.id) {
      fetchRecommendations();
      fetchSavedRecipes();
    }
  }, [session?.user?.id]);

  // Current recipe should always be the first non-swiped recipe in the recommendations array
  useEffect(() => {
    if (recommendations.length > 0) {
      setCurrentRecipe(recommendations[0]);
    } else {
      setCurrentRecipe(null);
    }
  }, [recommendations]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-b-2 border-orange-500"></div>
        </div>
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
    <div className="flex min-h-full flex-col justify-center px-4 py-4">
      <FYPRecipeCard
        recipe={currentRecipe}
        onSwipe={handleSwipe}
        onBookmark={handleBookmark}
        onAnimationComplete={handleNextRecipe}
        isSaved={currentRecipe ? savedRecipeIds.has(currentRecipe.id) : false}
      />

      {/* Preload images for the next recipes */}
      {recommendations.map((recipe) => (
        <RecipeImage
          key={recipe.id}
          src={recipe.image_url || ""}
          alt={recipe.title || ""}
          width={400}
          height={300}
          className="hidden"
          draggable={false}
          priority={true}
        />
      ))}
    </div>
  );
}
