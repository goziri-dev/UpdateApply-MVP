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
    description:
      "Keep one honest work profile. Paste a job description, edit the draft, and download a tailored PDF. Private beta — join the waitlist.",
  },
  twitter: {
    card: "summary_large_image",
    title,
    description:
      "Keep one honest work profile. Paste a job description, edit the draft, and download a tailored PDF. Private beta — join the waitlist.",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${sourceSans.variable} ${newsreader.variable}`}>
      <body>{children}</body>
    </html>
  );
}
