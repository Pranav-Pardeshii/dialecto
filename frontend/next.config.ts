import type { NextConfig } from "next";

const isStandalone = process.env.STANDALONE === "true" || process.platform !== "win32";

const nextConfig: NextConfig = {
  ...(isStandalone ? { output: "standalone" } : {}),
  reactStrictMode: true,
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${backendUrl}/health`,
      },
      {
        source: "/ready",
        destination: `${backendUrl}/ready`,
      },
    ];
  },
};

export default nextConfig;
