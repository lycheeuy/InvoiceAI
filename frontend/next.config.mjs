/** @type {import('next').NextConfig} */
const apiInternalUrl = (
  process.env.INVOICEAI_API_INTERNAL_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiInternalUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
