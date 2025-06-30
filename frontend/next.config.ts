import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "zestfulkitchen.com",
        port: "",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
