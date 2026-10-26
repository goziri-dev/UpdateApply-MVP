import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  async redirects() {
    return [
      {
        source: "/:path*",
        has: [{ type: "host", value: "www.updateapply.com" }],
        destination: "https://updateapply.com/:path*",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
