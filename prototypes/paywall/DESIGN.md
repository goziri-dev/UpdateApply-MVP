# Paywall / Credits — Design

## Inspiration

**Mobbin:** Unavailable this session (`plugin-mobbin-mobbin` not connected). Favour waived waiting and supplied screenshots.

**References (Favour-supplied):**
1. Apple-style product comparison (`inspo-apple.png`) — horizontal plan cards, name → benefit → price → pill CTA + secondary link, generous whitespace, calm light surface, carousel on narrow.
2. Care.com “Choose your access” (`inspo-care.png`) — comparison containment, paid vs limited contrast, checkmark feature lists, solid primary CTA vs quieter secondary (“Stay limited”).

**What we borrow:**
- Horizontal comparison of plans (not a Settings list)
- Clear per-card hierarchy + breathing room
- Stronger paid tiers vs quieter Free/limited
- Checkmarks for what’s included
- Soft entry (banner) + hard entry (modal → comparison)

**What we adapt / skip:**
- No product photography / color swatches
- Forest accent (`#1B4D3E`) instead of Apple blue or Care beige wash
- Four tiers: Free · PAYG · Lite · Plus (Lite = Recommended)
- Stripe Checkout is faked as a brief “redirect” then success
- Soft nudge + hard paywall keep Idea copy (“Keep tailoring”, “Maybe later”, etc.)

## Tokens

**Colors:**
- `--bg`: `#FFFFFF`
- `--stage`: `#F3F4F2` (comparison stage — cool soft, not cream)
- `--ink`: `#111111`
- `--muted`: `#6B6B6B`
- `--label`: `#3A3A3A`
- `--line-soft`: `#E8E8E8`
- `--surface-soft`: `#F5F5F5`
- `--link`: `#2F6FED`
- `--accent`: `#1B4D3E`
- `--accent-hover`: `#153D32`
- `--accent-soft`: mix accent 10% into white
- `--danger` / `--danger-bg`: `#9B2C2C` / `#F8E8E8`
- `--success-bg`: `#E8F2EE`
- `--warn-bg`: `#F7F1E4` (soft nudge only — warm tint, not terracotta UI)

**Spacing grid:** 8px

**Type scale (≤5):**
- Display: 32px / 700 Source Serif 4 (comparison / paywall titles)
- Title: 22px / 700 Source Serif 4 (plan names)
- Body: 15–16px / 500 Source Sans 3
- Label: 13px / 600 Source Sans 3
- Caption: 12px / 400 Source Sans 3

**Shape:** pill CTAs (`999px`); plan cards `20px` radius (interactive containers); stage `28px`

**Motion:**
- Soft banner enter: 240ms ease-out
- Paywall overlay: 220ms ease-out (opacity + 12px rise)
- Plan hover: 160ms ease
- Checkout fake: 900ms then success
- Toast: 200ms ease-out

## Edge-case checklist

- [x] Loading — balance skeleton + checkout busy on CTAs
- [x] Error — checkout failure banner + retry
- [x] Empty — Credits hub with 0 balance copy
- [x] Overflow — long plan benefit lines clamp; carousel on narrow

## Surfaces in prototype

1. Soft low-credits banner (1 left)
2. Hard paywall → comparison (“Keep tailoring” / choose plan)
3. Credits & plans page (full comparison hub)
4. Success return after fake Checkout
5. Loading / error stubs via reviewer controls
