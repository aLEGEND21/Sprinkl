"use client";

import NextImage, { ImageProps as NextImageProps } from "next/image";
import { useState } from "react";

interface RecipeImageProps extends Omit<NextImageProps, "onError"> {
  fallbackSrc?: string;
}

export function RecipeImage({
  src,
  fallbackSrc = "/placeholder.svg",
  alt,
  ...props
}: RecipeImageProps) {
  const [imgSrc, setImgSrc] = useState(src);

  const handleError = () => {
    if (imgSrc !== fallbackSrc) {
      setImgSrc(fallbackSrc);
    }
  };

  return <NextImage src={imgSrc} alt={alt} onError={handleError} {...props} />;
}
