import { cn } from "@/lib/utils";
import { ChefHat } from "lucide-react";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  showText?: boolean;
}

export function Logo({ size = "md", className, showText = true }: LogoProps) {
  const sizeClasses = {
    sm: {
      container: "h-6 w-6",
      icon: "h-4 w-4",
      text: "text-sm",
    },
    md: {
      container: "h-8 w-8",
      icon: "h-5 w-5",
      text: "text-lg",
    },
    lg: {
      container: "h-10 w-10",
      icon: "h-6 w-6",
      text: "text-xl",
    },
  } as const;

  return (
    <div className={cn("flex items-center space-x-2", className)}>
      <div
        aria-hidden
        className={cn(
          "bg-primary grid place-items-center rounded-xl",
          "aspect-square",
          sizeClasses[size].container,
        )}
      >
        <ChefHat className={cn("text-white", sizeClasses[size].icon)} />
      </div>
      {showText && (
        <span
          className={cn("text-foreground font-bold", sizeClasses[size].text)}
        >
          Sprinkl
        </span>
      )}
    </div>
  );
}
