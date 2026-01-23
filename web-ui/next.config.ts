import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    let apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://web-production-d9bfe.up.railway.app';
    console.log('API Rewrite Destination:', apiUrl);

    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
      {
        source: '/projects/:path*',
        destination: `${apiUrl}/projects/:path*`,
      },
    ];
  },
};

export default nextConfig;
