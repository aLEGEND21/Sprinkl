"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Bookmark,
  ChefHat,
  Clock,
  Heart,
  Search,
  Smartphone,
} from "lucide-react";
import { signIn } from "next-auth/react";
import Image from "next/image";
import Link from "next/link";

export default function LandingPage() {
  const features = [
    {
      icon: Heart,
      title: "Swipe to Discover",
      description:
        "Swipe right on recipes you love, left on ones you don't. It's that simple!",
      color: "text-red-500",
    },
    {
      icon: Bookmark,
      title: "Save Favorites",
      description:
        "Keep all your favorite recipes in one place for easy access anytime.",
      color: "text-orange-500",
    },
    {
      icon: Search,
      title: "Smart Search",
      description:
        "Find recipes by ingredients, cuisine, or cooking time with our powerful search.",
      color: "text-blue-500",
    },
    {
      icon: Smartphone,
      title: "Mobile First",
      description:
        "Designed for your phone with smooth animations and intuitive gestures.",
      color: "text-green-500",
    },
  ];

  return (
    <div className="bg-background min-h-screen">
      {/* Navigation */}
      <nav className="bg-background/80 border-border sticky top-0 z-50 border-b backdrop-blur-md">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <ChefHat className="h-8 w-8 text-orange-500" />
              <span className="text-foreground text-xl font-bold">Sprinkl</span>
            </div>
            <div className="flex items-center space-x-3">
              <Button
                variant="ghost"
                onClick={() =>
                  signIn("google", { callbackUrl: "/protected/fyp" })
                }
                className="hidden sm:inline-flex"
              >
                Log In
              </Button>
              <Button
                onClick={() =>
                  signIn("google", { callbackUrl: "/protected/fyp" })
                }
                className="bg-orange-500 hover:bg-orange-600"
              >
                Get Started
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-orange-50 to-red-50 dark:from-orange-950/20 dark:to-red-950/20" />
        <div className="relative container mx-auto px-6 py-16 lg:py-24">
          <div className="grid items-center gap-12 lg:grid-cols-2">
            {/* Hero Content */}
            <div className="space-y-6 text-center lg:space-y-8 lg:text-left">
              <div className="space-y-4">
                <h1 className="text-foreground text-4xl leading-tight font-bold lg:text-6xl">
                  Sprinkl
                </h1>
                <p className="text-muted-foreground text-xl font-semibold lg:text-2xl">
                  The only recipe app you'll ever need
                </p>
                <p className="text-muted-foreground mx-auto max-w-lg text-lg lg:mx-0">
                  It's Tinder for recipes. Swipe through thousands of recipes to
                  find your perfect meal.
                </p>
              </div>

              {/* HERO SECTION BUTTONS */}
              <div className="flex w-full flex-row gap-2 sm:gap-4">
                <Button
                  onClick={() =>
                    signIn("google", { callbackUrl: "/protected/fyp" })
                  }
                  size="lg"
                  className="min-w-0 flex-1 rounded-full bg-orange-500 py-5 text-lg text-white hover:bg-orange-600"
                >
                  Get Started
                </Button>
                <Button
                  onClick={() =>
                    signIn("google", { callbackUrl: "/protected/fyp" })
                  }
                  variant="outline"
                  size="lg"
                  className="min-w-0 flex-1 rounded-full border-2 bg-transparent py-5 text-lg"
                >
                  Log In
                </Button>
              </div>
            </div>

            {/* Hero Image/Mockup */}
            <div className="flex justify-center lg:justify-end">
              <div className="relative h-90 w-64 lg:h-96 lg:w-80">
                <div className="absolute inset-0 rotate-3 transform rounded-3xl bg-gradient-to-b from-orange-400 to-orange-600 shadow-2xl" />
                <div className="absolute inset-0 -rotate-1 transform rounded-3xl border bg-white shadow-xl dark:bg-gray-900">
                  <div className="flex h-full flex-col p-4 lg:p-6">
                    <Image
                      src="/placeholder.svg?height=200&width=280"
                      alt="Recipe preview"
                      width={280}
                      height={200}
                      className="mb-3 h-48 w-full rounded-2xl object-cover lg:h-48"
                    />
                    <h3 className="text-foreground mb-2 text-lg font-semibold">
                      Creamy Pasta Carbonara
                    </h3>
                    <div className="mb-3 flex items-center gap-2">
                      <Badge variant="secondary" className="text-sm">
                        Italian
                      </Badge>
                      <div className="text-muted-foreground flex items-center gap-1">
                        <Clock className="h-4 w-4" />
                        <span className="text-sm">20 min</span>
                      </div>
                    </div>
                    <div className="flex-1" />
                    <div className="flex justify-center gap-6">
                      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-100 lg:h-16 lg:w-16 dark:bg-red-900">
                        <span className="text-2xl text-red-500">✕</span>
                      </div>
                      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-green-100 lg:h-16 lg:w-16 dark:bg-green-900">
                        <Heart className="h-6 w-6 text-green-500 lg:h-7 lg:w-7" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="bg-muted/30 px-6 py-16 lg:py-24">
        <div className="container mx-auto max-w-6xl">
          <div className="mb-16 space-y-4 text-center">
            <h2 className="text-foreground text-3xl font-bold lg:text-5xl">
              Why You'll Love It
            </h2>
            <p className="text-muted-foreground mx-auto max-w-2xl text-lg lg:text-xl">
              Everything you need to discover and organize your favorite recipes
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {features.map((feature, index) => (
              <Card key={index} className="h-full">
                <CardContent className="p-6 text-center lg:p-8">
                  <div className="space-y-4">
                    <div className="flex justify-center">
                      <feature.icon
                        className={`h-12 w-12 lg:h-16 lg:w-16 ${feature.color}`}
                      />
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-foreground text-lg font-semibold lg:text-xl">
                        {feature.title}
                      </h3>
                      <p className="text-muted-foreground text-sm lg:text-base">
                        {feature.description}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="px-6 py-16 lg:py-24">
        <div className="container mx-auto max-w-4xl">
          <div className="mb-16 space-y-4 text-center">
            <h2 className="text-foreground text-3xl font-bold lg:text-5xl">
              How It Works
            </h2>
            <p className="text-muted-foreground text-lg lg:text-xl">
              Get started in three simple steps
            </p>
          </div>

          <div className="grid gap-8 md:grid-cols-3">
            {[
              {
                step: "1",
                title: "Browse Recipes",
                description:
                  "Swipe through curated recipes from around the world",
              },
              {
                step: "2",
                title: "Save Your Favorites",
                description:
                  "Tap the bookmark icon to save recipes you want to try",
              },
              {
                step: "3",
                title: "Start Cooking",
                description:
                  "Access full recipes with ingredients and instructions",
              },
            ].map((item, index) => (
              <div key={index} className="space-y-4 text-center">
                <div className="flex justify-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-orange-500 text-xl font-bold text-white lg:h-20 lg:w-20 lg:text-2xl">
                    {item.step}
                  </div>
                </div>
                <div className="space-y-2">
                  <h3 className="text-foreground text-lg font-semibold lg:text-xl">
                    {item.title}
                  </h3>
                  <p className="text-muted-foreground mx-auto max-w-xs text-sm lg:text-base">
                    {item.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-muted/30 px-6 py-16 lg:py-24">
        <div className="container mx-auto max-w-3xl space-y-8 text-center">
          <div className="space-y-4">
            <h2 className="text-foreground text-3xl font-bold lg:text-5xl">
              Ready to Get Started?
            </h2>
            <p className="text-muted-foreground mx-auto max-w-2xl text-lg lg:text-xl">
              Join thousands of food lovers discovering their next favorite meal
            </p>
          </div>

          {/* CTA SECTION BUTTONS */}
          <div className="mx-auto flex w-full flex-row justify-center gap-2 sm:gap-4">
            <Button
              onClick={() =>
                signIn("google", { callbackUrl: "/protected/fyp" })
              }
              size="lg"
              className="min-w-0 flex-1 rounded-full bg-orange-500 py-5 text-lg text-white hover:bg-orange-600"
            >
              Create Account
            </Button>
            <Button
              onClick={() =>
                signIn("google", { callbackUrl: "/protected/fyp" })
              }
              variant="outline"
              size="lg"
              className="min-w-0 flex-1 rounded-full border-2 bg-transparent py-5 text-lg"
            >
              Log In
            </Button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="border-border border-t px-6 py-8 lg:py-12">
        <div className="container mx-auto text-center">
          <div className="mb-4 flex items-center justify-center space-x-2">
            <ChefHat className="h-6 w-6 text-orange-500" />
            <span className="text-foreground text-lg font-bold">Sprinkl</span>
          </div>
          <p className="text-muted-foreground text-sm">
            © {new Date().getFullYear()} Sprinkl. Made with ❤️ by{" "}
            <Link
              href="https://github.com/aLEGEND21/"
              className="text-orange-500"
            >
              aLEGEND
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
