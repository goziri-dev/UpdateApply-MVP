# UpdateApply app

Flutter client for UpdateApply (auth + onboarding → resume reveal → Home / Applications / tailor).

## Run

```bash
cd app
flutter run -d chrome --dart-define-from-file=.env
```

Required `--dart-define` keys (see `.env.example` if present): `API_BASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`. Optional: `SUPABASE_AUTH_REDIRECT_URL`.

### Vercel (Flutter web)

Root Directory: `app`. Prefer Build Command `bash vercel-build.sh` (also set in `vercel.json` with Output `build/web`, Install `echo skip`).

`API_BASE_URL` is baked in at **build** time via `--dart-define`. Auth can work (Supabase in the browser) while the API still fails if the define was missing or still `http://localhost:8000` from a copied `.env`.

In the Vercel project → **Settings → Environment Variables**, set for Production (and Preview if used):

| Name | Value |
|------|--------|
| `API_BASE_URL` | `https://updateapply-mvp.fly.dev` (script remaps empty/localhost to this) |
| `SUPABASE_URL` | (same as local / Fly) |
| `SUPABASE_ANON_KEY` | (anon / publishable key) |

Then **Redeploy** (Deployments → … → Redeploy, without stale cache if offered). A new build is required; changing env alone does not rewrite the old JS.

### VS Code / Cursor launch tip

Prefer **UpdateApply (Chrome) — recommended** in `.vscode/launch.json` (`noDebug: true`, Chrome, `--web-port=5173`). Plain F5 debug on Flutter web often hangs on breakpoints / DWDS; use **UpdateApply (Chrome + debugger)** only when you need the debugger.

## Shell (post-onboarding)

After onboarding, authenticated routes use a `StatefulShellRoute` with three tabs:

| Tab | Path | Role |
|-----|------|------|
| Home | `/` | Master remade resume preview + **Tailor to a job description** CTA |
| Jobs For You | `/jobs-for-you` | Ranked shortlist from shared ATS ingest + your Job preferences |
| Applications | `/applications` | Tailored-version history (list → detail) |

**Tailor** (`/tailor`) is **not** a shell tab — opened from Home CTA, a Jobs For You card, Applications empty CTA, or detail “Tailor again” (optional `TailorLaunchArgs` via `GoRouter` extra).

Shell header **account menu**: email → **Settings** → Sign out. Home stays mini preview + Tailor only (no reset chrome).

| Route | Role |
|-------|------|
| `/settings` | Account settings; **Start over** (reset / re-onboard) |
| `/settings/match-preferences` | Job preferences (titles, place, seniority) — also linked from Jobs For You |
| `/resume/edit` | Hybrid edit (master or tailored via `extra`) |
| `/resume/deepen` | Optional guided / journal deepen for one role or project |

### Jobs For You

1. Set **Job preferences** under Settings (suggested titles from the profile; you confirm).
2. Open the **Jobs For You** tab — ranked cards from `GET /api/v1/jobs-for-you` (empty reasons `no_preferences` / `no_matches`). Cap is a labeled default.
3. Open a card → tailor screen prefills with the stored description; tailor sends `posting_id` so the draft gets `apply_url` from the server (never a client-supplied URL).
4. Paste a Greenhouse / Lever / Ashby careers URL on the shortlist to add a board **for everyone**. Jobs appear after the next shared ingest — not instantly. Unrecognized hosts show the server 400 in the form.
5. Strong-match pings land in the in-app notification log (banner when unread). The app does not auto-tailor or auto-apply.

UpdateApply is not a job board and does not apply for you. Deferred sources (Fantastic.jobs, Workday, etc.) are not wired in the client.

## Living master + edit harness

- **Edit master** — Home mini preview → modal → **Edit master resume** under Download → `/resume/edit`. Add/Remove experience & projects; Save → `PUT /api/v1/resume/document` (reindexes).
- **Edit tailored** — Application detail → edit → same form; Save → `PATCH /api/v1/applications/{id}` with `resume`.
- **Agentic harness** — Edit / Ask (Ask = resume + live web search; needs server `TAVILY_API_KEY`; never changes the form). Propose-only turns with session memory; Accept into form, then Save. Clear session when leaving.
- **Deepen** — From edit form on a role/project: choose **guided** (novel consultant Qs) or **journal** (freeform dump). Accept merges into the form; Save persists.

## Reset / re-onboard

Settings → confirm **Start over** → `POST /api/v1/onboarding/reset`. Clears master profile + vectors + stored PDF; **keeps Applications**. Hard gate returns to upload.

## Applications flow

1. Tailor succeeds → server always inserts a new `application` draft; Flutter shows “Saved as draft · vN” + **View in Applications**.
2. List (`ApplicationsListScreen`) — newest first; same company+role can appear many times as separate versions.
3. Detail (`/applications/:id`) — tailored preview, download PDF, **apply on employer site** when `apply_url` is present (from a Jobs For You posting), edit tailored resume, mark applied, tailor again.
4. Empty state — single CTA into `/tailor`.

Prototype (approved, then implemented): `prototypes/applications/`.

## OAuth (Flutter web)

Sign-in uses **same-tab** redirect (PKCE). The IdP returns to the current origin; you should end with **one** UpdateApply tab, not a leftover original + callback tab.

Pin a stable web origin when developing so Supabase allow-lists match:

```bash
flutter run -d chrome --web-port=5000 --dart-define-from-file=.env
```

In **Supabase Dashboard → Authentication → URL Configuration**, confirm:

| Field | Local example | Notes |
|-------|---------------|--------|
| Site URL | `http://localhost:5000` | Prefer the pinned `--web-port` origin |
| Redirect URLs | `http://localhost:5000` | Same origin; add production origins too |
| Redirect URLs | `io.updateapply.app://login-callback/` | Native deep link (when shipping mobile) |

Optional dart-define `SUPABASE_AUTH_REDIRECT_URL` overrides the redirect; on web leave it empty so the app uses `Uri.base.origin` (must still be allow-listed). Enable providers under **Authentication → Providers** (Google, GitHub, Notion, Email).

## Onboarding tone

The role/project chat is a **calm consultant conversation**, not a hiring interview. Copy and generated prompts invite honest detail (gaps, shared credit, underselling) without grilling.

## Parse timeouts (Flutter web)

On web, Dio’s `connectTimeout` is time until response **headers**. Resume `/parse` is a sync LLM call, so the client uses a raised per-request timeout in `OnboardingService.parse()`. Prefer a running API on `:8000` and a healthy OpenRouter key; timeouts surface as timeout copy, not “unreadable PDF.”

## Resume preview + PDF download

After Review, the flow opens **`/onboarding/reveal`** (`ResumeRevealScreen`; legacy `/onboarding/ready` is the same screen): full HTML preview of the remade master, **Download PDF**, then **Go to dashboard** (`complete` + gate refresh → `/`).

On Home, a **mini** letter-aspect preview (`ResumePreview` mini mode) taps into a modal with a larger preview + Download + **Edit master resume**. Application detail and tailor results reuse the same preview/download path for tailored `ResumeDocument` JSON. Surfaces use `ResumeService` → `GET/POST /api/v1/resume/html` (same server Jinja template as PDF). Default `template_id` is `classic`.

Download calls `POST /api/v1/resume/export`, then on **web** triggers a browser save via blob URL (`resume_download_web.dart`). Non-web builds stub and throw. Filename is derived from basics name when possible.

### Flutter web iframe caveat

Preview uses `HtmlElementView` + a registered `HTMLIFrameElement` (`srcdoc`) scaled to letter size. Platform view factories are keyed by `viewType` and reused across rebuilds/hot reload. If the preview goes blank, duplicates, or stops updating after code changes to the iframe layer, do a **full hot restart** (not just hot reload) so factories re-register cleanly. Mini mode sets `pointer-events: none` so the parent `InkWell` owns taps.
