import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    externalDir: true,
  },
  async redirects() {
    return [
      {
        source: "/manifesto",
        destination: "https://www.sardis.sh/manifesto",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
