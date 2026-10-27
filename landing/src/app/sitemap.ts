import type { MetadataRoute } from "next";

// Keep this fully static. `new Date()` forced on-demand rendering under
// Cache Components and made /sitemap.xml intermittently 500 for some crawlers.
export default function sitemap(): MetadataRoute.Sitemap {
  const site =
    process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ||
    "https://updateapply.com";

  return [
    {
      // Match layout canonical (no trailing slash).
      url: site,
      lastModified: "2026-10-26",
      changeFrequency: "weekly",
      priority: 1,
    },
  ];
}
