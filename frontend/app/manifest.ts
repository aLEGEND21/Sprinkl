import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Food App",
    short_name: "FoodApp",
    description:
      "The only recipe app you'll ever need. It's Tinder for recipes. Swipe through thousands of recipes to discover your next meal!",
    start_url: "/",
    display: "standalone",
    background_color: "#EAEAEA",
    theme_color: "#FFA500",
  };
}
