# Screen / flow: Auth (sign-in / sign-up)

**Primary action:** Sign in with email/password, or Continue with Google, so the
user can save a profile and tailor resumes.

**Happy path (A → B):**
1. Land on Sign in — mark + “Hello again” + “Sign in to continue”.
2. Enter email/password → Sign in, **or** tap Continue with Google (Supabase OAuth).
3. Optional: “Sign up” toggles matching layout (Create your account).
4. Optional: Reset Password? (prototype link; flow TBD).

**API / data available:**
- Supabase Auth: email/password + Google OAuth session (access JWT).
- Backend verifies JWT on protected routes.

**Constraints:**
- Web-first Flutter; OAuth redirect URLs required for Google return.
- **v1 OAuth UI: Google only** (GitHub / Notion out of scope for the auth surface).
- Flutter production screens await prototype approval (ui-design gate).
- Pill / minimal pattern is intentional (Favour reference).

**UX copy (real words):**
- Sign-in title: Hello again
- Sign-in sub: Sign in to continue
- Sign-up title: Create your account
- Sign-up sub: Sign up to start tailoring
- CTAs: Sign in / Sign up / Continue with Google
- Reset: Reset Password?
- Switch (in): Don’t have an account? Sign up
- Switch (up): Already have an account? Sign in
- Loading: Signing in… / Connecting…
- Error: Sign-in didn’t finish. Check your details or try Google again.
- Footer: Terms · Privacy
