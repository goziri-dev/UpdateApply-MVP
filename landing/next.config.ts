import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  // Next 16 defaults qualities to [75] only; allow 90 for sharp UI screenshots.
  images: {
    qualities: [75, 90],
  },
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
