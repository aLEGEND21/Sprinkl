import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
        port: "",
        pathname: "/**",
      },
      {
        protocol: "http",
        hostname: "**",
        port: "",
        pathname: "/**",
      },
    ],
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
