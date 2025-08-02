// manifest.ts is used to generate manifest.json for PWA
import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Sprinkl",
    short_name: "Sprinkl",
    description:
      "The only recipe app you'll ever need. It's Tinder for recipes. Swipe through thousands of recipes to discover your next meal!",
    start_url: "/",
    display: "standalone",
    background_color: "#EAEAEA",
    theme_color: "#FF6900",
  };
}
