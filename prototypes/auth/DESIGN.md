# Auth design tokens & Mobbin notes

## Mobbin inspiration

**Queries / flows searched:**
- iOS: “sign in with Google GitHub social OAuth login providers”
- iOS: “sign up create account email password or continue with social”
- Web: “login page with multiple OAuth provider buttons”

**Status:** Mobbin MCP authenticated, but `search_flows` requires a **paid Mobbin plan** (`https://mobbin.com/pricing`). No screen images or app names could be pulled.

**References (app + screen / pattern):** *blocked — pending paid Mobbin or Favour waiver*

**What we borrow (provisional, from UpdateApply brand + common OAuth patterns):**
- Single-column auth composition; brand as hero signal
- Stacked full-width provider buttons (Google / GitHub / Notion)
- Sign-in ↔ Sign-up toggle without separate marketing chrome
- Explicit loading + inline error states

**What we adapt / skip:**
- No purple SaaS gradient, cream+terracotta, or dense broadsheet
- No email/password fields in MVP
- Forest ink + parchment atmosphere from existing `AppTheme` seed `0xFF1B4D3E`

## Tokens

**Colors:**
- `--bg`: `#F3F0E8` parchment wash (atmosphere via grain + soft radial, not flat white)
- `--ink`: `#14241E` primary text
- `--muted`: `#5C6B64`
- `--accent`: `#1B4D3E` UpdateApply forest
- `--accent-hover`: `#153D32`
- `--surface`: `#FFFDF8`
- `--line`: `#D5D0C4`
- `--danger`: `#9B2C2C`
- `--danger-bg`: `#F8E8E8`
- Provider surfaces: Google white, GitHub `#24292F`, Notion `#191919`

**Spacing grid:** 8px

**Type scale (≤5):**
- Display: 40px / 700 (brand)
- Title: 24px / 600
- Body: 16px / 400
- Label: 14px / 500
- Caption: 12px / 400

**Fonts:** Fraunces (display/brand) + Source Sans 3 (UI) via Google Fonts

**Motion:**
- Panel enter: 280ms ease-out (opacity + 8px rise)
- Button press: 120ms ease
- Error slide: 200ms ease-out
- Tab underline: 180ms ease

## Edge-case checklist

- [x] Loading — “Connecting…” overlay on active provider
- [x] Error — inline alert with retry copy
- [x] Empty — linked-accounts panel empty state
- [x] Overflow — long error / long email truncation
