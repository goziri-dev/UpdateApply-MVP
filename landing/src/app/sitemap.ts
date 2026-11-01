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
      lastModified: "2026-11-01",
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${site}/pricing`,
      lastModified: "2026-11-01",
      changeFrequency: "weekly",
      priority: 0.9,
    },
    {
      url: `${site}/about`,
      lastModified: "2026-11-01",
      changeFrequency: "monthly",
      priority: 0.8,
    },
  ];
}
