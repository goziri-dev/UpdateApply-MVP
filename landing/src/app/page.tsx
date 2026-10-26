import Image from "next/image";

import { WaitlistForm } from "@/components/WaitlistForm";

const appUrl =
  process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, "") ||
  "https://app.updateapply.com";

export default function Home() {
  return (
    <>
      <a className="skip" href="#waitlist">
        Skip to the waitlist
      </a>

      <header className="nav">
        <div className="nav-inner">
          <a className="brand" href="#top">
            <span className="mark" aria-hidden="true">
              <span className="mark-letter">u</span>
              <span className="mark-plus">+</span>
            </span>
            <span className="brand-name">UpdateApply</span>
          </a>
          <nav className="nav-links" aria-label="Page">
            <a className="nav-text" href="#how">
              How it works
            </a>
            <a className="nav-cta" href="#waitlist">
              Join the waitlist
            </a>
          </nav>
        </div>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="headline">
          <div className="hero-copy">
            <p className="eyebrow">Private beta</p>
            <h1 id="headline">
              Tailor a resume for the job you’re <em>actually</em> applying to.
            </h1>
            <p className="lede">
              Keep one honest profile. Paste a job description, edit the draft,
              download a PDF — then apply on their site.
            </p>
            <WaitlistForm />
          </div>

          <div className="hero-visual" aria-hidden="true">
            <div className="hero-stage">
              <Image
                className="shot shot-hero"
                src="/assets/hero-tailor.jpg"
                width={2400}
                height={1439}
                alt=""
                priority
                quality={90}
                sizes="(max-width: 1120px) 100vw, 1120px"
              />
            </div>
          </div>
        </section>

        <section className="feature" id="how" aria-labelledby="feature-title">
          <div className="section-inner feature-inner">
            <h2 id="feature-title" className="display">
              Your draft, the job, and a clear next step.
            </h2>
            <p className="section-lede">
              Each tailored resume lives with the posting you pasted — so you
              can edit, download, and mark applied when you’ve sent it.
            </p>
            <div className="feature-stage">
              <Image
                className="shot shot-feature"
                src="/assets/feature-application.jpg"
                width={2400}
                height={1482}
                alt="Application detail with tailored resume preview and job description context"
                quality={90}
                sizes="(max-width: 1120px) 100vw, 1040px"
              />
            </div>
          </div>
        </section>

        <section className="points" aria-labelledby="points-title">
          <div className="section-inner">
            <h2 id="points-title" className="display">
              What you actually do
            </h2>
            <div className="points-grid">
              <article>
                <h3>Keep one profile</h3>
                <p>
                  Roles, projects, and skills stay in one place — the source of
                  truth for every tailor.
                </p>
              </article>
              <article>
                <h3>Paste the job</h3>
                <p>
                  UpdateApply writes a draft from what you already kept. It does
                  not invent experience you didn’t have.
                </p>
              </article>
              <article>
                <h3>Edit in plain language</h3>
                <p>
                  Ask for changes — keep one degree, tighten a summary — then
                  keep or discard the proposal.
                </p>
              </article>
              <article>
                <h3>Download, then apply</h3>
                <p>
                  Export a PDF and apply on the employer’s site. UpdateApply
                  does not submit applications for you.
                </p>
              </article>
            </div>

            <figure className="support-shot">
              <Image
                className="shot shot-support"
                src="/assets/feature-edit-agent.jpg"
                width={1800}
                height={974}
                alt="Edit tailored resume with an agent that proposes changes you can keep or discard"
                quality={90}
                sizes="(max-width: 760px) 100vw, 760px"
              />
              <figcaption>
                Describe a change. Review the proposal. Keep what’s honest.
              </figcaption>
            </figure>
          </div>
        </section>

        <section className="close" aria-labelledby="close-title">
          <div className="section-inner close-inner">
            <h2 id="close-title" className="display">
              The app isn’t open yet. The waitlist is.
            </h2>
            <p className="section-lede">
              Leave your email. We’ll write when a spot opens — this still
              doesn’t create an account or grant access.
            </p>
            <a className="btn btn-close" href="#waitlist">
              Join the waitlist
            </a>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="footer-inner">
          <p className="footer-brand">UpdateApply</p>
          <p>
            We’ll store your email so we can tell you when a spot opens. We
            don’t sell it.
          </p>
          <p>
            Already invited? <a href={appUrl}>Open the app</a>. Access is
            checked after you sign in. A waitlist email is not enough.
          </p>
        </div>
      </footer>
    </>
  );
}
