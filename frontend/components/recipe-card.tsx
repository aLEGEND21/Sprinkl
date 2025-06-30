"use client";

import type React from "react";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Bookmark,
  Clock,
  ExternalLink,
  Heart,
  X,
  ChevronUp,
  ChevronDown,
  Star,
} from "lucide-react";
import { Recipe, RecipeCardProps } from "@/types";

export function RecipeCard({ recipe, onSwipe, onBookmark }: RecipeCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);
  const startPos = useRef({ x: 0, y: 0 });

  const handleTouchStart = (e: React.TouchEvent) => {
    const touch = e.touches[0];
    startPos.current = { x: touch.clientX, y: touch.clientY };
    setIsDragging(true);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isDragging) return;

    const touch = e.touches[0];
    const deltaX = touch.clientX - startPos.current.x;
    const deltaY = touch.clientY - startPos.current.y;

    setDragOffset({ x: deltaX, y: deltaY });
  };

  const handleTouchEnd = () => {
    if (!isDragging) return;

    const threshold = 100;

    if (Math.abs(dragOffset.x) > threshold) {
      if (dragOffset.x > 0) {
        onSwipe("like");
      } else {
        onSwipe("dislike");
      }
    } else if (dragOffset.y < -50 && Math.abs(dragOffset.x) < 50) {
      setExpanded(!expanded);
    }

    setDragOffset({ x: 0, y: 0 });
    setIsDragging(false);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    startPos.current = { x: e.clientX, y: e.clientY };
    setIsDragging(true);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;

    const deltaX = e.clientX - startPos.current.x;
    const deltaY = e.clientY - startPos.current.y;

    setDragOffset({ x: deltaX, y: deltaY });
  };

  const handleMouseUp = () => {
    if (!isDragging) return;

    const threshold = 100;

    if (Math.abs(dragOffset.x) > threshold) {
      if (dragOffset.x > 0) {
        onSwipe("like");
      } else {
        onSwipe("dislike");
      }
    } else if (dragOffset.y < -50 && Math.abs(dragOffset.x) < 50) {
      setExpanded(!expanded);
    }

    setDragOffset({ x: 0, y: 0 });
    setIsDragging(false);
  };

  useEffect(() => {
    const handleMouseMoveGlobal = (e: MouseEvent) => {
      if (!isDragging) return;

      const deltaX = e.clientX - startPos.current.x;
      const deltaY = e.clientY - startPos.current.y;

      setDragOffset({ x: deltaX, y: deltaY });
    };

    const handleMouseUpGlobal = () => {
      if (!isDragging) return;

      const threshold = 100;

      if (Math.abs(dragOffset.x) > threshold) {
        if (dragOffset.x > 0) {
          onSwipe("like");
        } else {
          onSwipe("dislike");
        }
      }

      setDragOffset({ x: 0, y: 0 });
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMoveGlobal);
      document.addEventListener("mouseup", handleMouseUpGlobal);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMoveGlobal);
      document.removeEventListener("mouseup", handleMouseUpGlobal);
    };
  }, [isDragging, dragOffset.x, onSwipe]);

  const rotation = dragOffset.x * 0.1;
  const opacity = 1 - Math.abs(dragOffset.x) * 0.002;

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)]">
      <Card
        ref={cardRef}
        className="w-full max-w-sm mx-auto relative cursor-grab active:cursor-grabbing transition-all duration-200 shadow-lg"
        style={{
          transform: `translateX(${dragOffset.x}px) translateY(${dragOffset.y}px) rotate(${rotation}deg)`,
          opacity,
        }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      >
        {/* Swipe indicators */}
        {Math.abs(dragOffset.x) > 50 && (
          <div
            className={`absolute inset-0 flex items-center justify-center z-10 rounded-lg ${
              dragOffset.x > 0
                ? "bg-green-500/20 border-4 border-green-500"
                : "bg-red-500/20 border-4 border-red-500"
            }`}
          >
            <div
              className={`text-6xl font-bold ${
                dragOffset.x > 0 ? "text-green-500" : "text-red-500"
              }`}
            >
              {dragOffset.x > 0 ? "❤️" : "✕"}
            </div>
          </div>
        )}

        <CardContent className="p-0">
          <div className="relative">
            <Image
              src={
                recipe.image_url ||
                "https://via.placeholder.com/400x300/f3f4f6/6b7280?text=No+Image"
              }
              alt={recipe.title}
              width={400}
              height={300}
              className="w-full h-64 object-cover rounded-t-lg"
            />
            <Button
              onClick={(e) => {
                e.stopPropagation();
                onBookmark();
              }}
              variant="secondary"
              size="icon"
              className="absolute top-3 right-3 bg-white/90 hover:bg-white"
            >
              <Bookmark className="h-4 w-4" />
            </Button>
          </div>

          <div className="p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold text-gray-800 line-clamp-1">
                {recipe.title}
              </h3>
              <Button
                onClick={(e) => {
                  e.stopPropagation();
                  setExpanded(!expanded);
                }}
                variant="ghost"
                size="icon"
                className="shrink-0"
              >
                {expanded ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronUp className="h-4 w-4" />
                )}
              </Button>
            </div>

            <div className="flex items-center gap-3 mb-3">
              {recipe.total_time && (
                <div className="flex items-center gap-1 text-gray-600">
                  <Clock className="h-4 w-4" />
                  <span className="text-sm">{recipe.total_time} min</span>
                </div>
              )}
              {recipe.cuisine && (
                <Badge variant="secondary" className="text-xs">
                  {recipe.cuisine}
                </Badge>
              )}
              {recipe.category && (
                <Badge variant="outline" className="text-xs">
                  {recipe.category}
                </Badge>
              )}
              {recipe.overall_rating && (
                <div className="flex items-center gap-1">
                  <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                  <span className="text-xs text-gray-600">
                    {recipe.overall_rating.toFixed(1)}
                  </span>
                </div>
              )}
            </div>

            {recipe.description && (
              <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                {recipe.description}
              </p>
            )}

            {expanded && (
              <div className="space-y-4 border-t pt-4">
                <div>
                  <h4 className="font-medium text-gray-800 mb-2">
                    Ingredients:
                  </h4>
                  <ul className="text-sm text-gray-600 space-y-1">
                    {recipe.ingredients.map((ingredient, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <span className="text-orange-500 mt-1">•</span>
                        <span>{ingredient}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-gray-800 mb-2">
                    Instructions:
                  </h4>
                  <ol className="text-sm text-gray-600 space-y-2">
                    {recipe.instructions.map((instruction, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <span className="text-orange-500 font-medium min-w-[20px]">
                          {index + 1}.
                        </span>
                        <span>{instruction}</span>
                      </li>
                    ))}
                  </ol>
                </div>
                {recipe.keywords && recipe.keywords.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-800 mb-2">Tags:</h4>
                    <div className="flex flex-wrap gap-1">
                      {recipe.keywords.slice(0, 5).map((keyword, index) => (
                        <Badge
                          key={index}
                          variant="outline"
                          className="text-xs"
                        >
                          {keyword}
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
                    className="w-full bg-orange-500 hover:bg-orange-600"
                  >
                    <ExternalLink className="mr-2 h-4 w-4" />
                    View Full Recipe
                  </Button>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Action buttons */}
      <div className="flex items-center justify-center gap-6 mt-6">
        <Button
          onClick={() => onSwipe("dislike")}
          variant="outline"
          size="lg"
          className="rounded-full w-16 h-16 border-red-200 hover:bg-red-50 hover:border-red-300"
        >
          <X className="h-6 w-6 text-red-500" />
        </Button>
        <Button
          onClick={() => onSwipe("like")}
          variant="outline"
          size="lg"
          className="rounded-full w-16 h-16 border-green-200 hover:bg-green-50 hover:border-green-300"
        >
          <Heart className="h-6 w-6 text-green-500" />
        </Button>
      </div>

      <p className="text-center text-sm text-gray-500 mt-4 px-4">
        Swipe right to like, left to pass, or tap ↑ for details
      </p>
    </div>
  );
}
