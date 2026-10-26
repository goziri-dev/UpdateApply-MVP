import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const site =
    process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ||
    "https://updateapply.com";

  return [
    {
      // Match layout canonical (no trailing slash).
      url: site,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
    },
  ];
}
