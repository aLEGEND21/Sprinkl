import { cn } from "@/lib/utils";
import logoImage from "@/public/logo.png";
import Image from "next/image";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  showText?: boolean;
}

export function Logo({ size = "md", className, showText = true }: LogoProps) {
  const sizeClasses = {
    sm: {
      image: "h-4 w-4",
      text: "text-sm",
    },
    md: {
      image: "h-6 w-6",
      text: "text-lg",
    },
    lg: {
      image: "h-8 w-8",
      text: "text-xl",
    },
  };

  return (
    <div className={cn("flex items-center space-x-1", className)}>
      <Image
        src={logoImage}
        alt="Sprinkl Logo"
        className={cn("object-contain", sizeClasses[size].image)}
      />
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
