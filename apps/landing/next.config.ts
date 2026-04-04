import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    externalDir: true,
  },
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'cdn.brandfetch.io' },
      { protocol: 'https', hostname: 'asset.brandfetch.io' },
    ],
  },
};

export default nextConfig;
