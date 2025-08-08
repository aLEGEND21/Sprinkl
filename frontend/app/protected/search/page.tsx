"use client";

import { useState, useEffect, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Search, Clock, ExternalLink, Bookmark } from "lucide-react";
import { RecipeImage } from "@/components/ui/recipe-image";
import { Recipe } from "@/types/recipe";
import { useSession } from "next-auth/react";
import { toast } from "sonner";

interface SearchResponse {
  results: Recipe[];
  total_hits: number;
  page: number;
  size: number;
  query: string;
}

export default function SearchPage() {
  const { data: session } = useSession();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Recipe[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [totalResults, setTotalResults] = useState(0);
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [savedRecipeIds, setSavedRecipeIds] = useState<Set<string>>(new Set());

  const limit = 20;

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 500);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Reset pagination when query changes
  useEffect(() => {
    setOffset(0);
    setSearchResults([]);
    setHasMore(true);
  }, [debouncedQuery]);

  const searchRecipes = useCallback(
    async (query: string, currentOffset: number, append: boolean = false) => {
      if (!query.trim()) {
        setSearchResults([]);
        setTotalResults(0);
        setHasMore(false);
        return;
      }

      const loadingState =
        currentOffset === 0 ? setIsSearching : setIsLoadingMore;
      loadingState(true);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;
        const page = Math.floor(currentOffset / limit) + 1;
        const response = await fetch(
          `${apiUrl}/search?q=${encodeURIComponent(query)}&page=${page}&size=${limit}`,
        );

        if (response.ok) {
          const data: SearchResponse = await response.json();

          if (append) {
            setSearchResults((prev) => [...prev, ...data.results]);
          } else {
            setSearchResults(data.results);
          }

          setTotalResults(data.total_hits);
          setHasMore(currentOffset + data.results.length < data.total_hits);
        } else {
          toast.error("Search failed", {
            description: "Unable to search recipes",
          });
        }
      } catch (error) {
        toast.error("Search failed", { description: "Network error occurred" });
      } finally {
        loadingState(false);
      }
    },
    [],
  );

  // Search when debounced query changes
  useEffect(() => {
    if (debouncedQuery) {
      searchRecipes(debouncedQuery, 0, false);
    } else {
      setSearchResults([]);
      setTotalResults(0);
      setHasMore(false);
    }
  }, [debouncedQuery, searchRecipes]);

  const loadMore = useCallback(() => {
    if (!hasMore || isLoadingMore || !debouncedQuery) return;

    const newOffset = offset + limit;
    setOffset(newOffset);
    searchRecipes(debouncedQuery, newOffset, true);
  }, [hasMore, isLoadingMore, debouncedQuery, offset, searchRecipes]);

  // Fetch saved recipes when user is authenticated
  useEffect(() => {
    async function fetchSavedRecipes() {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const response = await fetch(
        `${apiUrl}/users/${session?.user?.id}/saved-recipes`,
      );

      if (response.ok) {
        const data = await response.json();
        const savedIds = new Set<string>(
          data.saved_recipes.map((recipe: Recipe) => recipe.id as string),
        );
        setSavedRecipeIds(savedIds);
      }
    }

    fetchSavedRecipes().catch(() => {
      toast.error("Failed to fetch saved recipes");
    });
  }, [session?.user]);

  const handleSaveRecipe = async (recipeId: string) => {
    if (!session?.user?.id) {
      toast.error("Please log in to save recipes");
      return;
    }

    const isCurrentlySaved = savedRecipeIds.has(recipeId);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;

    try {
      if (isCurrentlySaved) {
        // Unsave the recipe
        const response = await fetch(
          `${apiUrl}/users/${session.user.id}/saved-recipes/${recipeId}`,
          { method: "DELETE" },
        );

        if (response.ok) {
          setSavedRecipeIds((prev) => {
            const newSet = new Set(prev);
            newSet.delete(recipeId);
            return newSet;
          });
        } else {
          throw new Error("Failed to unsave recipe");
        }
      } else {
        // Save the recipe
        const response = await fetch(
          `${apiUrl}/users/${session.user.id}/saved-recipes/${recipeId}`,
          { method: "POST" },
        );

        if (response.ok) {
          setSavedRecipeIds((prev) => new Set([...prev, recipeId]));
        } else {
          throw new Error("Failed to save recipe");
        }
      }
    } catch (error) {
      toast.error("Error", {
        description: `Failed to ${isCurrentlySaved ? "unsave" : "save"} recipe`,
      });
    }
  };

  return (
    <div className="flex min-h-full flex-col px-4 pb-4">
      {/* Search Bar */}
      <div className="bg-background border-border sticky top-0 z-20 -mx-4 mb-4 border-b px-4 py-4">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 transform" />
            <Input
              placeholder="Search for hundreds of recipes"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
      </div>

      {/* Search Results */}
      {searchResults.length > 0 ? (
        <div className="space-y-4">
          <h2 className="text-foreground/80 text-md text-center font-semibold">
            Found {totalResults} matching recipe{totalResults !== 1 ? "s" : ""}
          </h2>
          <div className="grid grid-cols-2 items-stretch gap-3">
            {searchResults.map((recipe) => (
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
                      onClick={() => handleSaveRecipe(recipe.id)}
                      size="icon"
                      variant="outline"
                      className={`absolute top-2 right-2 z-10 bg-white/90 hover:bg-white dark:bg-gray-800/90 dark:hover:bg-gray-800 ${
                        savedRecipeIds.has(recipe.id) ? "text-yellow-500" : ""
                      }`}
                      title={
                        savedRecipeIds.has(recipe.id)
                          ? "Unsave Recipe"
                          : "Save Recipe"
                      }
                    >
                      <Bookmark
                        className={`h-4 w-4 ${savedRecipeIds.has(recipe.id) ? "fill-current" : ""}`}
                      />
                    </Button>
                  </div>
                  <div className="flex flex-1 flex-col p-3">
                    <h3 className="text-foreground mb-2 line-clamp-2 text-sm font-semibold">
                      {recipe.title}
                    </h3>
                    <div className="mb-3 flex flex-col gap-2">
                      <div className="text-muted-foreground flex items-center gap-2">
                        {recipe.total_time && (
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            <span className="text-xs">
                              {recipe.total_time} min
                            </span>
                          </div>
                        )}
                        {recipe.cuisine && (
                          <Badge variant="secondary" className="w-fit text-xs">
                            {recipe.cuisine}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <div className="mt-auto flex w-full gap-2">
                      {recipe.recipe_url && (
                        <Button
                          onClick={() =>
                            window.open(recipe.recipe_url, "_blank")
                          }
                          size="sm"
                          className="flex-1 bg-orange-500 text-xs hover:bg-orange-600"
                        >
                          <ExternalLink className="mr-1 h-3 w-3" />
                          View Recipe
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Load More Button */}
          {hasMore && (
            <div className="flex justify-center">
              <Button
                onClick={loadMore}
                disabled={isLoadingMore}
                variant="outline"
                className="w-full max-w-xs"
              >
                {isLoadingMore ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-b-2 border-orange-500"></div>
                ) : (
                  "Load More"
                )}
              </Button>
            </div>
          )}
        </div>
      ) : searchQuery && !isSearching ? (
        <div className="flex grow flex-col items-center justify-center text-center">
          <Search className="text-muted-foreground mx-auto mb-4 h-12 w-12" />
          <h3 className="text-foreground mb-2 text-lg font-medium">
            No recipes found
          </h3>
          <p className="text-muted-foreground">
            Try searching for different recipe titles
          </p>
        </div>
      ) : !searchQuery ? (
        <div className="flex grow flex-col items-center justify-center text-center">
          <Search className="text-muted-foreground mx-auto mb-4 h-12 w-12" />
          <h3 className="text-foreground mb-2 text-lg font-medium">
            Discover Recipes
          </h3>
          <p className="text-muted-foreground">Search for recipes by title</p>
        </div>
      ) : null}

      {/* Loading State */}
      {isSearching && (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-orange-500"></div>
        </div>
      )}
    </div>
  );
}
