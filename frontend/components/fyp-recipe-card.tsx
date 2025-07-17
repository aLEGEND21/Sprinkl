"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Recipe } from "@/types/recipe";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bookmark,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Heart,
  X,
} from "lucide-react";
import Image from "next/image";
import { useState } from "react";

interface FYPRecipeCardProps {
  recipe: Recipe;
  onSwipe: (swipe: "like" | "dislike") => void;
  onBookmark: () => void;
  isSaved?: boolean;
}

export function FYPRecipeCard({
  recipe,
  onSwipe,
  onBookmark,
  isSaved = false,
}: FYPRecipeCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const [swipeDirection, setSwipeDirection] = useState<
    "like" | "dislike" | null
  >(null);

  const handleSwipeAction = (action: "like" | "dislike") => {
    if (isAnimating) return;
    setIsAnimating(true);
    setSwipeDirection(action);

    // Call onSwipe immediately to mark recipe as swiped
    onSwipe(action);

    // Reset animation state after animation completes
    setTimeout(() => {
      setIsAnimating(false);
      setSwipeDirection(null);
      setExpanded(false);
    }, 300);
  };

  const slideVariants = {
    initial: { x: 0, rotate: 0, opacity: 1 },
    like: {
      x: 400,
      rotate: 15,
      opacity: 0,
      transition: { duration: 0.3, ease: "easeOut" as const },
    },
    dislike: {
      x: -400,
      rotate: -15,
      opacity: 0,
      transition: { duration: 0.3, ease: "easeOut" as const },
    },
  };

  return (
    <div className="flex min-h-[calc(100vh-8rem)] flex-col items-center justify-center">
      <AnimatePresence mode="wait">
        <motion.div
          key={recipe.id}
          className="relative mx-auto w-full max-w-sm"
          variants={slideVariants}
          initial="initial"
          animate={swipeDirection || "initial"}
          exit={swipeDirection === "like" ? "like" : "dislike"}
        >
          {/* Swipe overlay indicators */}
          <AnimatePresence>
            {swipeDirection && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className={`absolute inset-0 z-20 flex items-center justify-center rounded-lg ${
                  swipeDirection === "like"
                    ? "border-4 border-green-500 bg-green-500/20"
                    : "border-4 border-red-500 bg-red-500/20"
                }`}
              >
                <div
                  className={`text-6xl font-bold ${
                    swipeDirection === "like"
                      ? "text-green-500"
                      : "text-red-500"
                  }`}
                >
                  {swipeDirection === "like" ? "❤️" : "✕"}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <Card className="w-full shadow-lg transition-all duration-200 select-none">
            <CardContent className="-my-6 p-0">
              <div className="relative">
                <Image
                  src={recipe.image_url!}
                  alt={recipe.title!}
                  width={400}
                  height={300}
                  className="h-96 w-full rounded-t-lg object-cover"
                  draggable={false}
                  priority={true}
                />
                <Button
                  onClick={(e) => {
                    e.stopPropagation();
                    onBookmark();
                  }}
                  variant="secondary"
                  size="icon"
                  className={`absolute top-3 right-3 z-10 bg-white/90 hover:bg-white dark:bg-gray-800/90 dark:hover:bg-gray-800 ${
                    isSaved ? "text-yellow-500" : ""
                  }`}
                  disabled={isAnimating}
                >
                  <Bookmark
                    className={`h-4 w-4 ${isSaved ? "fill-current" : ""}`}
                  />
                </Button>

                {/* Tap areas for like/dislike */}
                <div className="absolute inset-0 flex">
                  {/* Left half - Dislike */}
                  <button
                    onClick={() => handleSwipeAction("dislike")}
                    disabled={isAnimating}
                    className="flex flex-1 items-center justify-center rounded-tl-lg bg-transparent transition-colors duration-200 hover:bg-red-500/10"
                    aria-label="Dislike recipe"
                  >
                    <div className="opacity-0 transition-opacity duration-200 hover:opacity-100">
                      <X className="h-8 w-8 text-red-500" />
                    </div>
                  </button>

                  {/* Right half - Like */}
                  <button
                    onClick={() => handleSwipeAction("like")}
                    disabled={isAnimating}
                    className="flex flex-1 items-center justify-center rounded-tr-lg bg-transparent transition-colors duration-200 hover:bg-green-500/10"
                    aria-label="Like recipe"
                  >
                    <div className="opacity-0 transition-opacity duration-200 hover:opacity-100">
                      <Heart className="h-8 w-8 text-green-500" />
                    </div>
                  </button>
                </div>
              </div>

              <div className="p-4">
                <div className="mb-2 flex items-start justify-between gap-2">
                  <h3 className="text-foreground line-clamp-2 text-lg font-semibold">
                    {recipe.title}
                  </h3>
                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      setExpanded(!expanded);
                    }}
                    variant="ghost"
                    size="icon"
                    className="-mt-0.5 shrink-0"
                    disabled={isAnimating}
                  >
                    {expanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronUp className="h-4 w-4" />
                    )}
                  </Button>
                </div>

                <div className="mb-3 flex items-center gap-3">
                  {recipe.cuisine && (
                    <Badge variant="secondary" className="text-xs">
                      {recipe.cuisine}
                    </Badge>
                  )}
                  {recipe.category && (
                    <Badge variant="secondary" className="text-xs">
                      {recipe.category}
                    </Badge>
                  )}
                  {typeof recipe.overall_rating === "number" && (
                    <Badge variant="secondary" className="text-xs">
                      <span className="mr-0.75">⭐</span>
                      {recipe.overall_rating.toFixed(1)}
                    </Badge>
                  )}
                </div>

                <AnimatePresence>
                  {expanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="border-border space-y-4 border-t pt-4">
                        {recipe.description && (
                          <div>
                            <h4 className="text-foreground mb-2 font-medium">
                              Description
                            </h4>
                            <p className="text-muted-foreground text-sm">
                              {recipe.description}
                            </p>
                          </div>
                        )}
                        <div>
                          <h4 className="text-foreground mb-2 font-medium">
                            Ingredients
                          </h4>
                          <ul className="text-muted-foreground [&>li::marker]:text-primary list-inside list-disc space-y-1 text-sm">
                            {recipe.ingredients.map((ingredient, idx) => (
                              <li key={idx} className="truncate">
                                {ingredient}
                              </li>
                            ))}
                          </ul>
                        </div>
                        {recipe.dietary_restrictions &&
                          recipe.dietary_restrictions.length > 0 && (
                            <div>
                              <h4 className="text-foreground mb-2 font-medium">
                                Dietary Restrictions
                              </h4>
                              <div className="flex flex-wrap gap-1">
                                {recipe.dietary_restrictions.map((dr, idx) => (
                                  <Badge
                                    key={idx}
                                    variant="outline"
                                    className="text-xs"
                                  >
                                    {dr}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}
                        {recipe.recipe_url && (
                          <Button
                            onClick={(e) => {
                              e.stopPropagation();
                              window.open(recipe.recipe_url, "_blank");
                            }}
                            className="mt-1 w-full"
                            disabled={isAnimating}
                            variant="default"
                          >
                            <ExternalLink className="mr-2 h-4 w-4" />
                            View Full Recipe
                          </Button>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </AnimatePresence>

      {/* Action buttons */}
      <div className="mt-6 flex items-center justify-center gap-6">
        <Button
          onClick={() => handleSwipeAction("dislike")}
          variant="outline"
          size="lg"
          className="h-16 w-16 rounded-full border-red-200 hover:border-red-300 hover:bg-red-50 dark:border-red-800 dark:hover:bg-red-950"
          disabled={isAnimating}
        >
          <X className="h-6 w-6 text-red-500" />
        </Button>
        <Button
          onClick={() => handleSwipeAction("like")}
          variant="outline"
          size="lg"
          className="h-16 w-16 rounded-full border-green-200 hover:border-green-300 hover:bg-green-50 dark:border-green-800 dark:hover:bg-green-950"
          disabled={isAnimating}
        >
          <Heart className="h-6 w-6 text-green-500" />
        </Button>
      </div>

      <div className="text-muted-foreground mt-4 mb-8 space-y-1 px-4 text-center text-sm">
        <p>Tap left side to pass, right side to like</p>
        <p>Or use the buttons above • Tap ↑ for details</p>
      </div>
    </div>
  );
}
