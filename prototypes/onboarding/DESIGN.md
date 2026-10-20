# Onboarding design — UpdateApply

## Inspiration

**Mobbin:** Skipped by Favour’s request (paywall). Do not re-enable without asking.

**References used instead:**
1. Attached progressive onboarding shell — Back + `N / M`, left content / right abstract resume illustration, soft spacious layout
2. Attached upload modal — dashed dropzone, Browse File, clear hierarchy (adapted to UpdateApply theme)
3. `prototypes/auth/` + `app/lib/core/theme/` — forest accent, Source Sans 3, 8px grid, alert/spinner patterns

**Borrowed from shell ref:** Top bar Back + step indicator, two-column split, breathable left copy, abstract profile illustration on the right.

**Borrowed from upload ref:** Dashed dropzone, “Choose a file or drag and drop”, Browse File affordance, primary Upload CTA below.

**Adapted / skipped:** No dark-green modal chrome, no peach CTA, no LinkedIn URL / Paste tabs, no .doc/.docx, no “Skip, add later”. PDF only, hard gate. Forest `#1B4D3E` CTA. Canvas stays close to auth white with soft grey surfaces (not parchment wash from older auth experiments).

## Tokens (maps to auth)

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
| `--danger` / `--danger-bg` | `#9B2C2C` / `#F8E8E8` | auth |
| Spacing | 8px grid | auth |
| Font | Source Sans 3 | auth / Google Fonts |
| Motion | 280ms rise, 120ms press, ease-out | auth |

**Onboarding-specific:** Slightly wider content column; soft surface panels for dropzone / interview card / illustration (not pill-only like auth — interaction surfaces use 12–16px radius). Mic button is circular (recording affordance).

## Flow map

1. **Upload** — PDF dropzone + browse; edge: empty, wrong type, oversize
2. **Parsing** — processing state until mock “experience list ready”
3. **Interview** — sample work role, then sample project; AI Q + mic + transcript; Next follow-up / Done with this item
4. **Review** — edit basics, experiences, projects (skills listed, not interviewed)
5. **Ready** — confirmation + CTA into Tailor

## Product assumptions (defaults)

- Hard gate: all roles + projects must be interviewed before Review → Ready
- Skills extracted from PDF are shown on Review but never interviewed
- After upload: full parse completes before interviews start (no chunk-streaming UI for v1)
- Turn budget ~3–5 follow-ups / ~2–3 min per item; user can say “that’s all” / Done
- Mic permission denied: inline alert + text answer fallback
- Max PDF ~10MB; LinkedIn export PDF OK to recommend in copy
