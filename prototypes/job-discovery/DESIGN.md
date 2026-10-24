# Jobs For You — UpdateApply

HTML/CSS prototype for **Jobs For You** (personalized discovery) and
**Job preferences** (under Settings). Not production Flutter. Iterate here
before app implementation.

## Status

**IA approved by Favour (2026-10-24)** and **Phase 0 implemented in Flutter +
server** (Jobs For You tab, Job preferences under Settings, propose + persist
APIs, stub shortlist empty reasons). Keep this folder as the visual reference.

Product renames locked:

- **Jobs For You** (was “Today’s matches”) — own primary shell tab
- **Job preferences** (was Match Preferences / “Confirm job targets” / “Job targets”) — Settings
- Shell: **Home · Jobs For You · Applications** (Settings via account menu)

## Idea brief (from Notion + Favour IA)

Sources:

- [Plan: Job discovery and daily shortlist](https://app.notion.com/p/40381aa8e0b581d1abeecb09f52eee37)
- [Build the daily shortlist screen](https://app.notion.com/p/40381aa8e0b5819c9db3dbe625131f13) (TSK-39)
- [Add confirm-targets flow on Home](https://app.notion.com/p/40381aa8e0b581b79e9efdb7d09791f6) (TSK-28) — **IA override:** screen moves to Settings as Job preferences, not a Home CTA
- [ADR: Public ATS boards…](https://app.notion.com/p/40381aa8e0b581bf80e3e532e947f90c)

**Primary action:** Browse ranked roles on Jobs For You; open one into tailor.
Configure titles / place / seniority in Settings → Job preferences.

**Happy path:**
1. Settings → Job preferences (titles + location/remote + seniority) → Save.
2. Jobs For You tab → filter by location / search company or role / filter by title.
3. Open a row → tailor prefilled with stored JD (user still runs tailor).
4. Download + apply on employer site (out of this prototype’s scope).

**Constraints:**
- Not a job board; not nested under Home.
- Shell is Home · Jobs For You · Applications (Settings via gear).
- Do not promise a fixed daily count while the cap is still a default.
- Empty: no preferences · nothing matched · search no-results · load error.

**UX copy (real words):**
- Tab / hero: **Jobs For You**
- Home teaser (optional): “Looking for roles that fit? Open Jobs For You”
- Settings row: **Job preferences** — Titles, location, and seniority for Jobs For You
- Prefs screen: **Job preferences** / Save preferences
- Empty no prefs: Set Job preferences first → Open Job preferences
- Empty no matches: No strong matches yet → Edit Job preferences
- Search empty: No results found
- Card: title · company · location · match reason · Open to tailor

## Inspiration

**Mobbin:** Unavailable — `plugin-mobbin-mobbin` not connected (same paid-plan
blocker as applications/auth). **Do not invent Mobbin citations.**

**Layout reference (Favour-attached):** Revolut Careers — location pill + search,
soft gray job cards, sidebar filters, empty “No results”.

**Primary references (in-repo):**
1. `prototypes/applications/` + `prototypes/auth/` — UpdateApply tokens & shell
2. `app/lib/core/theme/` — forest accent, Source Sans 3, 8px grid
3. `app/lib/features/settings/` — Settings as non-tab destination

**What we borrow from Revolut:**
- Location filter + search row under the hero
- Large soft surface cards
- Sidebar of filterable titles (not company departments)
- Explicit empty / no-results treatment

**What we adapt / skip:**
- No monochrome Revolut brand; use UpdateApply forest `#1B4D3E`
- No careers-board voice — personalized **Jobs For You**
- Discovery is a **primary tab**, not a Home subflow
- Preferences live in **Settings**, not as a main CTA on Home

## Tokens

Same as applications / Flutter theme:

| Token | Value |
| --- | --- |
| accent | `#1B4D3E` |
| accent-hover | `#153D32` |
| ink | `#111111` |
| muted | `#6B6B6B` |
| label | `#3A3A3A` |
| surface-soft | `#F5F5F5` |
| link | `#2F6FED` |
| spacing | 8px grid |
| type | Source Sans 3 — display 28/700, title 16/500, body 14–15, label 13, caption 12 |
| radius | 12 / 16 / pill 999 |
| motion | rise 280ms ease-out; card stagger 40ms; filter chip 160ms; search fade 200ms |

## Edge cases in prototype

- [x] Loading skeletons
- [x] Error + retry
- [x] Empty — no Job preferences set
- [x] Empty — preferences set, nothing matched
- [x] Empty — search/filter no results
- [x] Overflow — long job titles truncate

## Open questions for Favour

1. Jobs For You hero: keep the tab name as H1, or a softer “Current top matches” under it once the daily cap is chosen?
2. Sidebar “Your titles” — OK, or seniority / remote chips only?
3. After Save preferences, jump to Jobs For You (current) or stay on Settings?
4. Paste careers URL (Phase 3) — stub on Job preferences or Jobs For You?
5. Tab label length on mobile — “Jobs For You” vs shorter “Jobs”?
