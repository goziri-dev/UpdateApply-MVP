export const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ||
  "https://updateapply.com";

export const appUrl =
  process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, "") ||
  "https://app.updateapply.com";

export const ogImage = {
  url: "/assets/hero-tailor.jpg",
  width: 2400,
  height: 1439,
  alt: "UpdateApply tailor screen — resume draft beside a job posting",
} as const;
