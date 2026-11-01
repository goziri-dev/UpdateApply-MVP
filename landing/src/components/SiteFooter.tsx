import Link from "next/link";

import { appUrl } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-top">
          <p className="footer-brand">UpdateApply</p>
          <nav className="footer-nav" aria-label="Footer">
            <Link href="/">Home</Link>
            <Link href="/pricing">Pricing</Link>
            <Link href="/about">About</Link>
            <Link href="/#waitlist">Waitlist</Link>
          </nav>
        </div>
        <p>
          We’ll store the waitlist details you share so we can tell you when a
          spot opens. We don’t sell them.
        </p>
        <p>
          Already invited? <a href={appUrl}>Open the app</a>. Access is checked
          after you sign in. A waitlist email is not enough.
        </p>
      </div>
    </footer>
  );
}
