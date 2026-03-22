/** @type {import("next").NextConfig} */

const nextConfig = {
  reactStrictMode: true,
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Auth pages use useSearchParams — render them dynamically, not statically
  experimental: {
    missingSuspenseWithCSRBailout: false,
  },
  // Proxy API calls to FastAPI backend
  async rewrites() {
    return [
      {
        source: "/api/v2/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v2/:path*`,
      },
    ];
  },
  // better-auth API routes are handled by Next.js itself (/api/auth/*)
  // so they are NOT rewritten
};

export default nextConfig;
