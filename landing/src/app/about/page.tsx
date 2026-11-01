import type { Metadata } from "next";
import Link from "next/link";

import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { ogImage, siteUrl } from "@/lib/site";

const title = "About UpdateApply — honest resume tailoring";
const description =
  "UpdateApply helps job seekers land interviews by re-tailoring resumes to each pasted job description from one honest work profile. Built by Favour Akubuo.";
const ogDescription =
  "One honest profile. Paste a job description. Edit the draft. Download a PDF — then apply on their site. Built for solo job seekers.";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/about" },
  openGraph: {
    type: "website",
    siteName: "UpdateApply",
    url: "/about",
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
  "@graph": [
    {
      "@type": "AboutPage",
      "@id": `${siteUrl}/about#webpage`,
      url: `${siteUrl}/about`,
      name: title,
      description: ogDescription,
      isPartOf: { "@id": `${siteUrl}/#website` },
      about: { "@id": `${siteUrl}/#organization` },
    },
    {
      "@type": "Organization",
      "@id": `${siteUrl}/#organization`,
      name: "UpdateApply",
      url: siteUrl,
      logo: `${siteUrl}/icon.png`,
      description: ogDescription,
      founder: {
        "@type": "Person",
        name: "Favour Akubuo",
      },
    },
  ],
};

export default function AboutPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <a className="skip" href="#about">
        Skip to about
      </a>

      <SiteHeader active="about" />

      <main id="top">
        <section className="page-hero" aria-labelledby="about-title">
          <p className="eyebrow">About us</p>
          <h1 id="about-title">
            Built for people who apply to many roles — and refuse to invent
            experience.
          </h1>
          <p className="lede">
            UpdateApply helps job seekers land interviews by re-tailoring a
            resume to each pasted job description from one persisted, honest
            profile.
          </p>
        </section>

        <section className="about-body" id="about" aria-labelledby="why-title">
          <div className="section-inner about-inner">
            <article className="about-block">
              <h2 id="why-title" className="display about-display">
                Why it exists
              </h2>
              <p>
                Job seekers waste hours rewriting the same history for every
                posting. Generic CVs underperform; the details that already live
                in past roles and skills are hard to reuse consistently. The
                problem isn’t “more AI fluff” — it’s getting a truthful draft
                aligned to <em>this</em> job, fast enough that you still apply.
              </p>
            </article>

            <article className="about-block">
              <h2 className="display about-display">What we believe</h2>
              <p>
                Keep one source of truth for your work. Paste the job. Get a
                structured draft you can edit in plain language — keep or discard
                proposals — then download a PDF and apply on the employer’s
                site. UpdateApply does not invent experience you didn’t have,
                and it does not submit applications for you.
              </p>
            </article>

            <article className="about-block">
              <h2 className="display about-display">How the product works</h2>
              <ul className="about-list">
                <li>
                  <strong>One profile.</strong> Roles, projects, and skills stay
                  in a living master resume that improves subsequent tailorings.
                </li>
                <li>
                  <strong>Paste a job description.</strong> The backend rewrites
                  from what you already kept — not from thin air.
                </li>
                <li>
                  <strong>Edit, then export.</strong> Manual edits or an
                  agentic proposal you accept; PDF on demand from your browser.
                </li>
                <li>
                  <strong>Applications history.</strong> Each tailored version
                  lives with the posting you pasted so you can track what you
                  sent — not a full ATS pipeline.
                </li>
              </ul>
            </article>

            <article className="about-block">
              <h2 className="display about-display">Who’s behind it</h2>
              <p>
                UpdateApply is built by{" "}
                <strong>Favour Akubuo</strong> (Goziri) — a solo product effort
                focused on web-first resume tooling for people in an active job
                search. Private beta is invite-gated on purpose: the core loop
                ships first, then hardening, privacy, and billing — without
                turning the landing page into a fake team page.
              </p>
            </article>

            <article className="about-block">
              <h2 className="display about-display">What we’re not</h2>
              <p>
                Not a job board that applies for you. Not a place that stores
                your PDF forever as the source of truth. Not a promise that
                signing the waitlist opens the app. Invited users sign in at the
                app host; the waitlist only tells us when to write.
              </p>
            </article>
          </div>
        </section>

        <section className="close" aria-labelledby="about-close">
          <div className="section-inner close-inner">
            <h2 id="about-close" className="display">
              Follow the work
            </h2>
            <p className="section-lede">
              Join the waitlist if you’re searching now. See{" "}
              <Link href="/pricing">pricing</Link> for how tailorings are
              metered once billing opens.
            </p>
            <Link className="btn btn-close" href="/#waitlist">
              Join the waitlist
            </Link>
          </div>
        </section>
      </main>

      <SiteFooter />
    </>
  );
}
