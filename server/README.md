# UpdateApply server

FastAPI + SQLModel API: Supabase JWT auth, resume onboarding (upload → parse → conversation → review).

## Run

```bash
cd server
uv run app
```

Listens on `0.0.0.0:8000` by default. Copy `.env` from your secrets (never commit).

## Job discovery (Phases 0–3)

Shared ATS ingest — **no user id**. A new user does **not** increase ATS HTTP traffic. Matching and notify are **per user** against shared `job_posting` + that user's Job preferences and `profile_chunk` embeddings. Tailor runs only when the user opens a posting (`POST /api/v1/tailor`). Tavily stays Ask-mode only.

```bash
cd server
uv run alembic upgrade head
uv run updateapply-catalog seed-boards             # bounded JSON seed
uv run updateapply-catalog import-directory --download   # full CC-BY-4.0 directory (~10k)
uv run updateapply-catalog ingest                  # active boards → job_posting
uv run updateapply-catalog ingest --slug linear    # optional single board
uv run updateapply-catalog normalize-locations
uv run updateapply-catalog embed-postings          # needs OPENROUTER_API_KEY
uv run updateapply-catalog notify                  # strong matches → in-app log
uv run updateapply-catalog daily                   # locked: ingest → normalize → embed → notify
```

### Daily ingest

Prefer **OS cron** (or launchd) calling the same CLI — smallest clock, no queue framework:

```cron
0 6 * * * cd /path/to/UpdateApply/server && uv run updateapply-catalog daily
```

Overlapping runs share a file lock under `data/locks/daily_job_run.lock`. Optional in-process loop: `ENABLE_DAILY_JOB_RUNNER=true` + `DAILY_JOB_RUNNER_HOUR_UTC=6` (still uses the same locked `run_daily`).

### Routes

| Route | Role |
|-------|------|
| `GET/PUT/DELETE /api/v1/match-preferences` | Job preferences (per user) |
| `GET /api/v1/jobs-for-you` | Ranked shortlist (labeled default cap) |
| `POST /api/v1/jobs-for-you/{id}/open` | Mark opened |
| `POST /api/v1/company-boards/from-url` | Detect Greenhouse/Lever/Ashby URL → `company_board` (next ingest fetches; no scrape) |
| `GET /api/v1/match-notifications` | In-app notify log |

### Notify (Decision)

- Cap **3**/user/day · similarity floor **0.35** · channel **in-app log** (+ optional `NOTIFY_WEBHOOK_URL`)
- Stamps `match_ledger.notified_at`; unique `(user_id, posting_id)` prevents repeats
- Copy must not claim a job was “posted yesterday” as fact (vendor timestamps are approximate)

### Catalog notes

- Tables: `company_board`, `job_posting`, `match_ledger`, `match_notification`
- Bounded seed JSON under `data/seeds/`; full directory is CC-BY-4.0 — see `data/ATTRIBUTION-ats-company-directory.md`
- Ingest upserts on `(vendor, external_job_id)`; JD text only when new/changed; Greenhouse detail: `…/boards/{slug}/jobs/{id}`
- 404 / repeated failures → `company_board.status = unavailable`. Pause: `INGEST_HOST_PAUSE_SECONDS` (default `0.75`)
- **Not built:** Fantastic.jobs fetcher, Workday, applicant counts, LinkedIn/Indeed, Apify, TheirStack

## Onboarding conversation

`InterviewQuestionService` generates **calm consultant** prompts per role/project (`INTERVIEW_SYSTEM_PROMPT` in `app/services/interview_questions.py`).

Cached scripts live under `profile._onboarding.item_scripts` with `script_version`. Bump `INTERVIEW_SCRIPT_VERSION` when the prompt/tone changes so stale scripts regenerate.

Interview answers are stored under `profile._onboarding.item_transcripts` (not dumped into public bullets). After the conversation, `POST /api/v1/onboarding/review/generate` runs `AgentTask.PROFILE_REVIEW` to rewrite an evergreen master resume for Review. Bump `PROFILE_REVIEW_VERSION` in `app/services/profile_review.py` when the rewrite prompt changes.

## OpenRouter

`AgentFactory` sets a **60s** request timeout on every chat client. Without that, a stalled provider can hang sync `/parse` indefinitely (Flutter looks “frozen”).

Task → default model: see `app/core/llm_tasks.py`. Override with `OPENROUTER_MODEL_*` env vars when needed.

**Resume edit default model:** `google/gemini-2.5-flash` (same cheap Flash tier as extract — chosen for format-following / minimal diffs, not a premium bump). Override with `OPENROUTER_MODEL_RESUME_EDIT` if you want heavier judgment (e.g. `openai/gpt-4o`).

Interview mic STT uses OpenRouter `POST /api/v1/audio/transcriptions` (default `openai/whisper-1`). Override with `OPENROUTER_MODEL_INTERVIEW_TRANSCRIBE`. Audio is transcribed in memory and not stored. Endpoint: `POST /api/v1/onboarding/interview/transcribe`.

### Resume edit harness

`POST /api/v1/resume/edit` is a multi-turn agentic propose endpoint (does **not** persist). Modes:

| `mode` | Behavior |
|--------|----------|
| `edit` (default) | Minimal-diff rewrite; preserves date/link formats; returns proposed `resume` + `detail` summary |
| `ask` | Live web search (Tavily, query grounded in matching resume employers/schools) + resume → answer in `detail` (with research notes) and optional `confidence`; never mutates: `applied=false`, `resume` unchanged. Change requests get a short answer and a nudge to Edit |

Legacy `advise` / `research_propose` values are accepted and treated as `ask`.

**Session memory (MVP):** server keeps an in-memory session per `session_id` (scoped to the authenticated user). Pass `session_id` from the prior response to continue (“also shorten that bullet”). Optional `prior_outcome`: `accepted` \| `rejected` for the last proposal. Clear with `DELETE /api/v1/resume/edit/session/{session_id}` when leaving the edit screen or resetting.

**Limits:** process-local (lost on restart / not shared across workers); TTL ~1 hour idle; ~40 turns / ~500 sessions capped. Fine for single-process local/dev.

**Ask:** requires `TAVILY_API_KEY`. Without it, `ask` returns HTTP 400 (`research_unavailable`) with a clear “not configured” message — Edit still works.

### Living-master voice deepen

Optional enrichment for **one** experience or project after onboarding (Add/Remove rows live in the Flutter form). Does **not** flip onboarding status/gate. Prefer item-level rewrite over full-master remake. Client **Accept** merges into the editor; **Save** calls `PUT /resume/document` (master) or `PATCH /applications/{id}` (tailored) → persist + reindex.

Two paths (`mode` on start, or journal shortcut):

| Path | How | Notes |
|------|-----|--------|
| `guided` (default) | Novel short consultant Qs → turn → propose | Excludes prior onboarding + `_deepen` prompts for that item |
| `journal` | Freeform dump via `POST /deepen/journal` | Optional one clarify, else enriched proposal |

Whisper reuse: `POST /api/v1/onboarding/interview/transcribe`. Sessions are in-memory (same limits as edit). Asked themes land under profile `_deepen` so later deepens stay novel.

### Reset / re-onboard

| Method | Path | Notes |
|--------|------|--------|
| `POST` | `/api/v1/onboarding/reset` | Clears master `profile.data`, `profile_chunk` vectors, stored resume PDF; returns `status=not_started`. **Keeps Applications.** |

Flutter entry: Settings → Start over.

## Tailor + pgvector RAG

Primary vectors come from the **approved remade master profile** (bullets, summaries, skills, light role metadata) — not transcripts or the raw CV extract alone. Decision: Notion Docs “Embedding = remade master profile chunks”.

- Embedding model: `openai/text-embedding-3-small` (1536 dims). Override: `OPENROUTER_MODEL_EMBEDDING`.
- Table: `profile_chunk` (Alembic `b2c3d4e5f6a7`). Re-index replaces prior chunks for the user on onboarding `complete`, onboarding profile PUT (review edits), and `PUT /api/v1/profile`.
- `POST /api/v1/tailor` embeds the pasted JD, retrieves top-k chunks, and runs `AgentTask.RESUME_TAILOR` → validated `ResumeDocument`. Stub only when `ALLOW_STUB_PARSE` and no OpenRouter key.
- On success, tailor **always inserts a new** `application` draft row (JSONB `resume_document`; PDFs not stored). Same company+role can appear many times as separate versions. `TailorResponse` always includes `application_id` + `application_version` on success (Flutter deep-links to Applications).

## Applications (tailored history)

Table: `application` (Alembic `c3d4e5f6a7b8`). Auth required (`DbUser`). Newest first on list.

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/api/v1/applications` | List summaries (company, role, status, version, JD snippet, dates) |
| `GET` | `/api/v1/applications/{id}` | Detail + full `resume` document |
| `POST` | `/api/v1/applications/{id}/mark-applied` | Sets `status=applied`, `applied_at` (optional body override) |
| `PATCH` | `/api/v1/applications/{id}` | Optional company / role / status / applied_at / **`resume`** (full tailored `ResumeDocument` after hybrid edit) |
| `DELETE` | `/api/v1/applications/{id}` | Remove one tailored version (204). Does not renumber remaining versions. |

No unique constraint on company+role. Master remade profile stays on Home / profile routes — Applications only stores tailored versions.

## Resume preview + PDF export

Content SSOT is `ResumeDocument` JSON (master profile mapped via `profile_to_resume_document`, or a tailored document). Presentation is versioned HTML/CSS under `app/templates/resume/<id>/<version>/` (each folder: `template.html` + `styles.css`) — the LLM never emits HTML. Registry: `app/services/resume_render.py` (`classic` → `classic/v1` today).

All routes require `Authorization: Bearer <supabase_access_token>` (`DbUser`).

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/api/v1/resume/templates` | List `{id, name, version, description}` |
| `GET` | `/api/v1/resume/document` | Master remade profile as `ResumeDocument` |
| `PUT` | `/api/v1/resume/document` | Persist master `ResumeDocument` → profile + reindex (keeps `_onboarding`) |
| `POST` | `/api/v1/resume/edit` | Body: `{resume, instruction, mode?, session_id?, prior_outcome?}` → `{resume, detail, mode, session_id, applied, confidence?}` (no persist) |
| `DELETE` | `/api/v1/resume/edit/session/{session_id}` | Clear in-memory edit session (204) |
| `POST` | `/api/v1/resume/deepen/start` | Optional deepen for one experience/project (`{resume, section, index, mode?}`) — `guided` \| `journal`; no onboarding gate flip |
| `POST` | `/api/v1/resume/deepen/journal` | Freeform journal dump → optional clarify or proposal (`{resume, section, index, text, skip_clarify?}`) |
| `GET` | `/api/v1/resume/deepen/{session_id}` | Current deepen question / coverage |
| `POST` | `/api/v1/resume/deepen/turn` | Submit transcript (or `force_done`) for current deepen question |
| `POST` | `/api/v1/resume/deepen/propose` | Item-level rewrite from transcripts → proposed `item` + merged `resume` (no persist) |
| `DELETE` | `/api/v1/resume/deepen/{session_id}` | Clear deepen session (204) |
| `GET` | `/api/v1/resume/html?template_id=classic` | Jinja HTML for iframe (master). Unknown id → 404 |
| `POST` | `/api/v1/resume/html` | Body: `{template_id, resume?}`. Omit `resume` → master; pass tailored JSON for job-specific preview |
| `POST` | `/api/v1/resume/export` | Same body → `application/pdf` (`Content-Disposition` attachment). Empty master → 400 |

**PDF engine: PyMuPDF `Story`** (not WeasyPrint / Playwright). Same Jinja-filled HTML/CSS as the Flutter iframe; reuses `pymupdf` (also used for upload ingest). No Pango/Cairo or Chromium sidecar. PDFs are on demand — not stored. Layout/export failure → 503.

### Smoke-test export

After onboarding (remade master profile exists) and with a valid access token:

```bash
TOKEN='…'   # Supabase session access_token

curl -sS "http://localhost:8000/api/v1/resume/html?template_id=classic" \
  -H "Authorization: Bearer $TOKEN" -o /tmp/resume.html

curl -sS -X POST http://localhost:8000/api/v1/resume/export \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"template_id":"classic"}' \
  -o /tmp/resume.pdf

file /tmp/resume.pdf   # expect PDF document
```

Omit `resume` to export the master; pass a full `ResumeDocument` under `resume` for a tailored PDF.

## Auth

JWT verify order: JWKS → HS256 (`SUPABASE_JWT_SECRET`) → Auth `get_user` fallback. Requires `SUPABASE_URL` + `SUPABASE_ANON_KEY`.
