import type { Metadata } from "next";
import Link from "next/link";

import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { ogImage, siteUrl } from "@/lib/site";

const title = "Pricing — UpdateApply resume tailoring plans";
const description =
  "UpdateApply pricing in EUR: Free (3 lifetime tailorings), Pay as you go €2.99, Lite €9.99/mo (10), Plus €14.99/mo (25). Private beta — join the waitlist.";
const ogDescription =
  "Free 3 lifetime tailorings, then Pay as you go, Lite, or Plus. One credit = one tailored resume. Private beta waitlist.";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/pricing" },
  openGraph: {
    type: "website",
    siteName: "UpdateApply",
    url: "/pricing",
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

const plans = [
  {
    id: "free",
    name: "Free",
    badge: "Limited",
    badgeClass: "plan-badge-limited",
    cardClass: "is-limited",
    benefit: "Try UpdateApply with a small lifetime grant — enough to see the fit.",
    price: "€0",
    meta: "3 tailorings · lifetime",
    features: [
      "3 CV tailorings on your account",
      "Full tailor + applications flow",
      "No monthly commitment",
    ],
    cta: "Join the waitlist",
    ctaClass: "btn-quiet",
  },
  {
    id: "payg",
    name: "Pay as you go",
    badge: "One-time",
    badgeClass: "plan-badge-one",
    cardClass: "",
    benefit: "One more tailored resume when you need it — no subscription.",
    price: "€2.99",
    meta: "1 additional tailoring",
    features: [
      "1 additional CV tailoring",
      "Credits stay on your account",
      "Buy again anytime",
    ],
    cta: "Join the waitlist",
    ctaClass: "btn",
  },
  {
    id: "lite",
    name: "Lite",
    badge: "Recommended",
    badgeClass: "plan-badge-rec",
    cardClass: "is-recommended",
    benefit:
      "Steady monthly tailorings for an active search without overbuying.",
    price: "€9.99",
    meta: "10 tailorings / month",
    features: [
      "10 CV tailorings every month",
      "Best per-tailoring value for most",
      "Cancel anytime once billing opens",
    ],
    cta: "Join the waitlist",
    ctaClass: "btn",
  },
  {
    id: "plus",
    name: "Plus",
    badge: "High volume",
    badgeClass: "plan-badge-rec",
    cardClass: "",
    benefit: "More room when you’re applying across many roles each week.",
    price: "€14.99",
    meta: "25 tailorings / month",
    features: [
      "25 CV tailorings every month",
      "Lowest cost per tailor",
      "Cancel anytime once billing opens",
    ],
    cta: "Join the waitlist",
    ctaClass: "btn",
  },
] as const;

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "SoftwareApplication",
      "@id": `${siteUrl}/#software`,
      name: "UpdateApply",
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      url: siteUrl,
      description: ogDescription,
      offers: {
        "@type": "AggregateOffer",
        priceCurrency: "EUR",
        lowPrice: "0",
        highPrice: "14.99",
        offerCount: 4,
        offers: [
          {
            "@type": "Offer",
            name: "Free",
            price: "0",
            priceCurrency: "EUR",
            description: "3 CV tailorings lifetime",
          },
          {
            "@type": "Offer",
            name: "Pay as you go",
            price: "2.99",
            priceCurrency: "EUR",
            description: "1 additional CV tailoring",
          },
          {
            "@type": "Offer",
            name: "Lite",
            price: "9.99",
            priceCurrency: "EUR",
            description: "10 CV tailorings per month",
            billingDuration: "P1M",
          },
          {
            "@type": "Offer",
            name: "Plus",
            price: "14.99",
            priceCurrency: "EUR",
            description: "25 CV tailorings per month",
            billingDuration: "P1M",
          },
        ],
      },
    },
    {
      "@type": "FAQPage",
      mainEntity: [
        {
          "@type": "Question",
          name: "What counts as a CV tailoring?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "One credit is one successful tailor that saves a tailored resume for a job description. Downloading a PDF of an already tailored version does not use another credit.",
          },
        },
        {
          "@type": "Question",
          name: "Does the Free plan renew every month?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "No. Free includes 3 CV tailorings for the lifetime of your account, not a monthly refresh.",
          },
        },
        {
          "@type": "Question",
          name: "Can I buy credits now?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "The product is in private beta. Join the waitlist on updateapply.com; invited users sign in at app.updateapply.com. Billing opens in the app once your account is allowed.",
          },
        },
      ],
    },
  ],
};

export default function PricingPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <a className="skip" href="#plans">
        Skip to plans
      </a>

      <SiteHeader active="pricing" />

      <main id="top">
        <section className="page-hero" aria-labelledby="pricing-title">
          <p className="eyebrow">Pricing</p>
          <h1 id="pricing-title">Choose your access</h1>
          <p className="lede">
            Free gets you started. Top up one at a time, or unlock a monthly
            pack when you’re applying hard. Prices in EUR. One credit = one
            tailored resume.
          </p>
        </section>

        <section
          className="pricing"
          id="plans"
          aria-labelledby="plans-heading"
        >
          <h2 id="plans-heading" className="sr-only">
            Plans
          </h2>
          <div className="section-inner">
            <div className="compare-stage">
              <div className="plan-rail">
                {plans.map((plan) => (
                  <article
                    key={plan.id}
                    className={`plan-card ${plan.cardClass}`.trim()}
                  >
                    <span className={`plan-badge ${plan.badgeClass}`}>
                      {plan.badge}
                    </span>
                    <h3 className="plan-name">{plan.name}</h3>
                    <p className="plan-benefit">{plan.benefit}</p>
                    <p className="plan-price">{plan.price}</p>
                    <p className="plan-meta">{plan.meta}</p>
                    <ul className="plan-features">
                      {plan.features.map((feature) => (
                        <li key={feature}>{feature}</li>
                      ))}
                    </ul>
                    <div className="plan-cta-row">
                      <Link
                        className={`btn ${plan.ctaClass === "btn-quiet" ? "btn-quiet" : ""}`.trim()}
                        href="/#waitlist"
                      >
                        {plan.cta}
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            </div>

            <p className="pricing-note">
              Private beta: joining the waitlist does not create an account or
              charge a card. Invited users manage plans in the app after sign-in.
            </p>
          </div>
        </section>

        <section className="faq" aria-labelledby="faq-title">
          <div className="section-inner faq-inner">
            <h2 id="faq-title" className="display">
              Common questions
            </h2>
            <dl className="faq-list">
              <div>
                <dt>What counts as a CV tailoring?</dt>
                <dd>
                  One credit is one successful tailor that saves a tailored
                  resume for a job description. Previewing or downloading a PDF
                  of an already tailored version does not use another credit.
                </dd>
              </div>
              <div>
                <dt>Does Free renew every month?</dt>
                <dd>
                  No. Free is a lifetime grant of 3 tailorings on your account —
                  not a monthly refresh.
                </dd>
              </div>
              <div>
                <dt>Do unused monthly credits roll over?</dt>
                <dd>
                  Lite and Plus allowances reset each billing month. Unused
                  monthly credits do not roll over. Pay-as-you-go credits stay
                  on your balance.
                </dd>
              </div>
              <div>
                <dt>Does UpdateApply apply for me?</dt>
                <dd>
                  No. You download a PDF and apply on the employer’s site.
                  UpdateApply does not submit applications for you.
                </dd>
              </div>
            </dl>
          </div>
        </section>

        <section className="close" aria-labelledby="pricing-close">
          <div className="section-inner close-inner">
            <h2 id="pricing-close" className="display">
              Start on the waitlist
            </h2>
            <p className="section-lede">
              Spots open in private beta. We’ll write when yours is ready —
              then you can try Free and upgrade in the app.
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
