# Screen / flow: Auth (sign-in / sign-up / link providers)

**Primary action:** Start OAuth with Google, GitHub, or Notion so the user can save a profile and tailor resumes.

**Happy path (A → B):**
1. Land on Sign in (default) — brand + one line of intent.
2. Tap a provider → Supabase OAuth → redirect back with session.
3. Optional: switch to Sign up (same providers; first visit creates the account).
4. Optional later: Connected accounts screen to link another provider.

**API / data available:**
- Supabase Auth session (access JWT) after OAuth.
- Backend verifies JWT on protected routes; providers configured in Supabase Dashboard.

**Constraints:**
- Web-first Flutter; deep link / redirect URLs required for OAuth return.
- No email/password in MVP (OAuth only).
- Flutter production screens await prototype approval (ui-design gate).

**UX copy (real words):**
- Title (sign-in): Welcome back
- Title (sign-up): Create your UpdateApply account
- Body: Tailor resumes to each job description — sign in to keep your profile.
- CTAs: Continue with Google / Continue with GitHub / Continue with Notion
- Helper: Same providers either way — we’ll create an account if you’re new.
- Loading: Connecting…
- Error: Sign-in didn’t finish. Try again or pick another provider.
- Empty (linked accounts): No other providers linked yet.
