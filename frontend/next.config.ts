import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    unoptimized: true, // Allow images to be served from any external domain
  },
  async redirects() {
    return [
      {
        source: "/login",
        has: [{ type: "query", key: "callbackUrl" }],
        destination: "/api/auth/signin/google?callbackUrl=:callbackUrl",
        permanent: false,
      },
      {
        source: "/login",
        destination: "/api/auth/signin/google",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
