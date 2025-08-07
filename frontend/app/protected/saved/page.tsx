"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RecipeImage } from "@/components/ui/recipe-image";
import { Clock, ExternalLink, Bookmark } from "lucide-react";
import { Trash } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useSession } from "next-auth/react";
import { Recipe } from "@/types";

export default function SavedRecipes() {
  const router = useRouter();
  const { data: session } = useSession();
  const [savedRecipes, setSavedRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSavedRecipes = async () => {
      if (!session?.user?.id) {
        setSavedRecipes([]);
        setLoading(false);
        return;
      }
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;
        const response = await fetch(
          `${apiUrl}/users/${session.user.id}/saved-recipes`,
        );
        if (response.ok) {
          const data = await response.json();
          setSavedRecipes(data.saved_recipes);
        } else {
          setSavedRecipes([]);
        }
      } catch (error) {
        setSavedRecipes([]);
      } finally {
        setLoading(false);
      }
    };
    if (session?.user?.id) {
      fetchSavedRecipes();
    }
  }, [session]);

  const handleUnsaveRecipe = async (recipeId: string) => {
    if (!session?.user?.id) return;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    try {
      const response = await fetch(
        `${apiUrl}/users/${session.user.id}/saved-recipes/${recipeId}`,
        { method: "DELETE" },
      );
      if (response.ok) {
        setSavedRecipes((prev) =>
          prev.filter((recipe) => recipe.id !== recipeId),
        );
        const recipeTitle =
          savedRecipes.find((recipe) => recipe.id === recipeId)?.title ||
          "recipe";
        toast.success("Bookmark removed", {
          description: `Removed bookmark from ${recipeTitle}`,
        });
      } else {
        throw new Error("Failed to unsave recipe");
      }
    } catch (error) {
      toast.error("Failed to unsave recipe");
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center pt-4">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-orange-500"></div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col px-4 pt-4 pb-4">
      {savedRecipes.length === 0 ? (
        <div className="flex h-full flex-col items-center justify-center text-center">
          <Bookmark className="text-muted-foreground mx-auto mb-4 h-12 w-12" />
          <h3 className="text-foreground mb-2 text-lg font-medium">
            No saved recipes yet
          </h3>
          <p className="text-muted-foreground mb-4">
            Start swiping to save your favorite recipes
          </p>
          <Button
            onClick={() => router.push("/fyp")}
            className="bg-orange-500 hover:bg-orange-600"
          >
            Discover Recipes
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          <h2 className="text-foreground/80 text-center text-lg font-semibold">
            {savedRecipes.length} saved recipe
            {savedRecipes.length !== 1 ? "s" : ""}
          </h2>
          <div className="grid grid-cols-2 items-stretch gap-3">
            {savedRecipes.map((recipe) => (
              <Card
                key={recipe.id}
                className="flex h-full flex-col overflow-hidden"
              >
                <CardContent className="-my-6 flex h-full flex-1 flex-col p-0">
                  <div className="relative">
                    <RecipeImage
                      src={recipe.image_url || ""}
                      alt={recipe.title}
                      width={200}
                      height={120}
                      className="h-32 w-full object-cover"
                    />
                    <Button
                      onClick={() => handleUnsaveRecipe(recipe.id)}
                      size="icon"
                      variant="outline"
                      className="absolute top-2 right-2 z-10 bg-white/90 text-red-600 hover:bg-white dark:bg-gray-800/90 dark:hover:bg-gray-800"
                      title="Unsave"
                    >
                      <Trash className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="flex flex-1 flex-col p-3">
                    <h3 className="text-foreground mb-2 line-clamp-2 text-sm font-semibold">
                      {recipe.title}
                    </h3>
                    <div className="mb-3 flex flex-col gap-2">
                      <div className="text-muted-foreground flex items-center gap-2">
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          <span className="text-xs">
                            {recipe.total_time} min
                          </span>
                        </div>
                        <Badge variant="secondary" className="w-fit text-xs">
                          {recipe.cuisine}
                        </Badge>
                      </div>
                    </div>
                    <div className="mt-auto flex w-full gap-2">
                      <Button
                        onClick={() => window.open(recipe.recipe_url, "_blank")}
                        size="sm"
                        className="flex-1 bg-orange-500 text-xs hover:bg-orange-600"
                      >
                        <ExternalLink className="mr-1 h-3 w-3" />
                        View Recipe
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
