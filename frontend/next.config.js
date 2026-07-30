/** @type {import('next').NextConfig} */
const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api-backend/:path*",
        destination: `${BACKEND_URL}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
