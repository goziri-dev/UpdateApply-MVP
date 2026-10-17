# Auth design tokens & direction

## Direction choice (this iteration)

**Refero-style structure + UpdateApply forest accent — not parchment wash.**

Favour supplied a Refero-style sign-in screenshot (Mobbin waived/blocked). That
reference is centered, white, high-whitespace, and pill-shaped. The previous
parchment/card auth prototype fought that pattern, so this pass:

- **Canvas:** pure white (`#FFFFFF`), no grain / radial wash
- **Shape language:** full pills for inputs + CTAs (explicit override of “avoid
  pills” taste rules — Favour chose this pattern)
- **Brand:** small rounded-square mark (`u` + `+`) in forest `#1B4D3E`, matching
  the product seed color; primary “Sign in / Sign up” button uses the same forest
  instead of pure black so UpdateApply still reads without drowning the minimal layout
- **Links:** blue `#2F6FED` for affordance (Reset / Sign up / Sign in), as in the
  reference
- **OAuth:** Google → GitHub → Notion — stacked light grey pills under an “or”
  divider (same pill style for all three)

Pure B&W was considered; forest on mark + primary CTA keeps brand identity with
almost the same calm as the reference.

### Brand mark (provisional)

The forest `u+` mark in the prototype is **provisional / not an official logo**.
Favour asked whether it will become official; do **not** invent a new logo.
Leave the mark as-is until Favour decides.

## Inspiration

**Source:** Favour’s Refero-style screenshot (attached in chat), not Mobbin.

**What we borrow:**
- Centered single column, generous vertical whitespace
- Brand mark → headline → short sub → labeled fields → primary CTA → mode switch → or → OAuth stack → Terms/Privacy
- Pill inputs with labels above; Reset Password? right under password
- Sign-in ↔ Sign-up via text link (same layout)

**What we adapt / skip:**
- Refero “p+” mark → UpdateApply provisional `u+` forest mark (see above)
- Copy adapted for UpdateApply (no Refero branding)
- OAuth order approved by Favour: Google, then GitHub, then Notion (same grey pill)
- Email/password kept (as in reference), plus the three OAuth providers

## Tokens

**Colors:**
- `--bg`: `#FFFFFF`
- `--ink`: `#111111`
- `--muted`: `#6B6B6B`
- `--label`: `#3A3A3A`
- `--line`: `#111111` (input border)
- `--surface-soft`: `#F5F5F5` (OAuth buttons)
- `--link`: `#2F6FED`
- `--accent`: `#1B4D3E` (mark + primary CTA)
- `--accent-hover`: `#153D32`
- `--danger` / `--danger-bg`: `#9B2C2C` / `#F8E8E8`

**Spacing grid:** 8px

**Type scale (≤5):**
- Headline: 28px / 700
- Sub: 16px / 500
- Body / control: 15px / 500–600
- Label: 13px / 600
- Caption / legal: 12px / 400

**Fonts:** Source Sans 3 (UI) via Google Fonts — clean sans to match the reference

**Shape:** `--pill: 999px` on inputs and buttons; mark radius 12px

**Motion:**
- Page enter: 280ms ease-out (opacity + 8px rise)
- Button press: 120ms ease
- Error: 200ms ease-out
- Focus ring: accent at 18% mix

## Edge-case checklist

- [x] Loading — primary / OAuth show spinner + “Signing in…” / “Connecting…”
- [x] Error — inline alert above the form
- [x] Empty — placeholder email when cleared (demo starts filled)
- [x] Overflow — long error wraps; column capped at 340px
