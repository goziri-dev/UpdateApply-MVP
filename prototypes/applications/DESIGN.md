# Applications design — UpdateApply

HTML/CSS prototype for the **Applications** tracker (tailored-resume history).
**Shipped** in Flutter + server on `feat/application-tracker` (commit after
approval). Keep this folder as the visual reference; Flutter is SSOT for
runtime behavior.

## Status

**Approved by Favour (2026-10-24)** with nav + body-title cleanup:

- Top nav is **Home · Applications** only.
- **Tailor is not a top-level tab** (and no “Tailor a job” chip in the shell header).
- Entry to tailor: Home’s **Tailor to a job description** CTA (existing `/tailor`
  route), plus contextual CTAs on Applications empty / detail (“Tailor again”).
- **No redundant tab-name headlines in body.** Shell tabs already say Home /
  Applications — do not repeat those words as page H1s.

**Implemented (2026-10-24)** on branch `feat/application-tracker` (Flutter shell +
server `application` APIs). In Flutter, center the Home/Applications tab control
(do not copy the prototype’s slight right bias).

## Idea brief (agreed product decisions)

**Primary action:** Browse tailored application history; open a version; download /
mark applied / tailor again.

**Happy path:**
1. After onboarding, shell exposes Home (master) · Applications.
2. User starts tailor from Home CTA (or Applications empty / Tailor again) → draft
   appears under Applications (company · role · version).
3. User opens a version → preview + actions (download, mark applied, tailor again).
4. Same company/role can appear multiple times as separate versions — never unique
   on company+role alone.

**API / data (shipped):** `application` table + `/api/v1/applications*` (see
`server/README.md`). Tailor response includes `application_id` +
`application_version`. Master remade resume stays on Home.

**Constraints:** Prototype remains under `prototypes/applications/` as design
reference. Web-first shell (matches current app).

**UX copy:**
- Home body: no “Home” title — lead with **Your resume** label + preview +
  tailor helper + CTA
- Applications body: no “Applications” H1 — optional light meta (`N saved`)
  above the list; empty starts with empty copy + CTA only
- Empty: No applications yet / Tailor your first job description
- List row: Company · Role · status/date · version · JD snippet
- Detail identity: Company · Role (content, not a tab name)
- Detail actions: Download · Mark as applied · Tailor again
- Sheet: Saved as draft · View in Applications · Keep editing (dismiss)

## Inspiration

**Mobbin:** Blocked — paid plan required after `mcp_auth`
(`https://mobbin.com/pricing`). Same blocker as auth (2026-10-17) and onboarding
(Favour skipped). **Do not invent Mobbin screen citations.** Re-run Mobbin when
Favour has access; until then inspiration is UpdateApply’s own language + common
list/detail patterns already used in auth/onboarding prototypes.

**Primary references (in-repo):**
1. `prototypes/auth/` + `prototypes/onboarding/` — forest accent, Source Sans 3,
   8px grid, white canvas, soft surfaces, pill CTAs, alert/spinner patterns
2. `app/lib/core/theme/` — Flutter tokens mapped 1:1 from auth
3. Home today: master resume + Tailor CTA; Applications is the history sibling

**What we borrow:**
- Calm white canvas; forest `#1B4D3E` primary; soft `#F5F5F5` panels
- Top chrome with clear hierarchy; one job per view
- Empty state with single primary CTA
- List rows as interactive surfaces (hairline rules / soft hover), not card soup
- Bottom sheet / toast-style confirmation after save (onboarding-style radius 12–16)

**What we adapt / skip:**
- No parchment wash, purple SaaS gradients, or cream+terracotta
- No pipeline kanban / stages in this pass (Applications ≠ full ATS board)
- Master resume preview stays on Home — Applications only shows tailored versions
- Provisional `u+` mark reused; not a new logo

## Tokens (maps to auth / Flutter)

| Token | Value | Source |
| --- | --- | --- |
| `--bg` | `#FFFFFF` | auth |
| `--ink` | `#111111` | auth |
| `--muted` | `#6B6B6B` | auth |
| `--label` | `#3A3A3A` | auth |
| `--line` | `#111111` | auth |
| `--line-soft` | `#E8E8E8` | auth |
| `--surface-soft` | `#F5F5F5` | auth |
| `--link` | `#2F6FED` | auth |
| `--accent` | `#1B4D3E` | auth / Flutter primary |
| `--accent-hover` | `#153D32` | auth |
| `--accent-soft` | mix accent 10% / white | onboarding |
| `--success` / `--success-bg` | `#1B4D3E` / `#E8F2EE` | onboarding |
| `--danger` / `--danger-bg` | `#9B2C2C` / `#F8E8E8` | auth |
| Spacing | 8px grid | auth |
| Font | Source Sans 3 | auth |
| Radius | 12px panels; pills on CTAs | onboarding + auth |
| Motion | 280ms rise, 200ms sheet, 120ms press, ease-out | auth |

**Type scale (≤5):**
- Display / page title: 28px / 700
- Section / company: 16–18px / 600–700
- Body: 15px / 500
- Meta / label: 13px / 600
- Caption / snippet: 12–13px / 400–500

## Shell

**Top nav tabs:** Home · Applications only.

| Dest | Role | How reached |
| --- | --- | --- |
| Home | Master remade resume + primary Tailor CTA | Top nav |
| Applications | Tailored-version history | Top nav |
| Tailor (`/tailor`) | Form + result — **not** a nav tab | Home CTA; Applications empty CTA; detail “Tailor again” |

Prototype uses a compact top nav (web-first). Bottom tabs remain an open question
for smaller viewports.

**Flutter note (2026-10-24):** Home no longer hosts debug/session chrome (Verify
session, Sign out, status strips). Account actions live in a lightweight shell
header menu (email + Sign out) — not a full Settings product; not shown in the
HTML prototype demo dock.

## Edge-case checklist

- [x] Empty — no applications + Tailor CTA
- [x] Loading — list skeleton rows
- [x] Error — inline alert (“Couldn’t load applications”)
- [x] Overflow — long company/role/snippet truncate with ellipsis
- [x] Versioning — two Stripe · Product Designer rows (v1 applied, v2 draft)
- [x] Draft confirmation — sheet after tailor save

## Prototype map

| Demo control | View |
| --- | --- |
| Empty | Applications empty state |
| List | Populated Applications list |
| Detail | One tailored resume preview + actions |
| Draft saved | List + confirmation sheet |
| Loading | Skeleton list |
| Error | List error alert |

Open `index.html` in a browser. Use the Demo dock to flip states.
