import type { Metadata } from "next";
import { Newsreader, Source_Sans_3 } from "next/font/google";

import "./globals.css";

const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-source-sans",
  display: "swap",
});

const newsreader = Newsreader({
  subsets: ["latin"],
  weight: ["500", "600"],
  style: ["normal", "italic"],
  variable: "--font-newsreader",
  display: "swap",
});

const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ||
  "https://updateapply.com";

const title = "UpdateApply — Tailor your resume to each job";
const description =
  "Keep one honest work profile. Paste a job description, edit the draft, and download a tailored PDF. Private beta — join the waitlist. Signing up does not open the app.";

const ogDescription =
  "Keep one honest work profile. Paste a job description, edit the draft, and download a tailored PDF. Private beta — join the waitlist.";

const ogImage = {
  url: "/assets/hero-tailor.jpg",
  width: 1024,
  height: 613,
  alt: "UpdateApply tailor screen — resume draft beside a job posting",
};

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title,
  description,
  robots: { index: true, follow: true },
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    siteName: "UpdateApply",
    url: "/",
    title,
    description: ogDescription,
    images: [ogImage],
  },
  twitter: {
    card: "summary_large_image",
    title,
    description: ogDescription,
    images: [ogImage.url],
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "UpdateApply",
  url: siteUrl,
  description: ogDescription,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${sourceSans.variable} ${newsreader.variable}`}>
      <body>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        {children}
      </body>
    </html>
  );
}
