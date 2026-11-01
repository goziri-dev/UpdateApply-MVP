import Link from "next/link";

type NavKey = "home" | "pricing" | "about";

type SiteHeaderProps = {
  active?: NavKey;
};

export function SiteHeader({ active }: SiteHeaderProps) {
  return (
    <header className="nav">
      <div className="nav-inner">
        <Link className="brand" href="/">
          <span className="mark" aria-hidden="true">
            <span className="mark-letter">u</span>
            <span className="mark-plus">+</span>
          </span>
          <span className="brand-name">UpdateApply</span>
        </Link>
        <nav className="nav-links" aria-label="Primary">
          <Link
            className={`nav-text${active === "pricing" ? " is-active" : ""}`}
            href="/pricing"
            aria-current={active === "pricing" ? "page" : undefined}
          >
            Pricing
          </Link>
          <Link
            className={`nav-text${active === "about" ? " is-active" : ""}`}
            href="/about"
            aria-current={active === "about" ? "page" : undefined}
          >
            About
          </Link>
          {active === "home" ? (
            <a className="nav-text" href="#how">
              How it works
            </a>
          ) : (
            <Link className="nav-text" href="/#how">
              How it works
            </Link>
          )}
          {active === "home" ? (
            <a className="nav-cta" href="#waitlist">
              Join the waitlist
            </a>
          ) : (
            <Link className="nav-cta" href="/#waitlist">
              Join the waitlist
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
