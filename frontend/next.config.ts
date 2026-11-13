import type { NextConfig } from "next";

// Le navigateur appelle /api sur la même origine que le frontend : le cookie de session reste first-party.
const apiUrl = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiUrl}/api/:path*` }];
  },
};

export default nextConfig;
