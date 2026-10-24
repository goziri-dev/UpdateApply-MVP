# UpdateApply server

FastAPI + SQLModel API: Supabase JWT auth, resume onboarding (upload → parse → conversation → review).

## Run

```bash
cd server
uv run app
```

Listens on `0.0.0.0:8000` by default. Copy `.env` from your secrets (never commit).

## Onboarding conversation

`InterviewQuestionService` generates **calm consultant** prompts per role/project (`INTERVIEW_SYSTEM_PROMPT` in `app/services/interview_questions.py`).

Cached scripts live under `profile._onboarding.item_scripts` with `script_version`. Bump `INTERVIEW_SCRIPT_VERSION` when the prompt/tone changes so stale scripts regenerate.

Interview answers are stored under `profile._onboarding.item_transcripts` (not dumped into public bullets). After the conversation, `POST /api/v1/onboarding/review/generate` runs `AgentTask.PROFILE_REVIEW` to rewrite an evergreen master resume for Review. Bump `PROFILE_REVIEW_VERSION` in `app/services/profile_review.py` when the rewrite prompt changes.

## OpenRouter

`AgentFactory` sets a **60s** request timeout on every chat client. Without that, a stalled provider can hang sync `/parse` indefinitely (Flutter looks “frozen”).

Task → default model: see `app/core/llm_tasks.py`. Override with `OPENROUTER_MODEL_*` env vars when needed.

Interview mic STT uses OpenRouter `POST /api/v1/audio/transcriptions` (default `openai/whisper-1`). Override with `OPENROUTER_MODEL_INTERVIEW_TRANSCRIBE`. Audio is transcribed in memory and not stored. Endpoint: `POST /api/v1/onboarding/interview/transcribe`.

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
| `PATCH` | `/api/v1/applications/{id}` | Optional company / role / status / applied_at |

No unique constraint on company+role. Master remade profile stays on Home / profile routes — Applications only stores tailored versions.

## Resume preview + PDF export

Content SSOT is `ResumeDocument` JSON (master profile mapped via `profile_to_resume_document`, or a tailored document). Presentation is versioned HTML/CSS under `app/templates/resume/<id>/<version>/` (each folder: `template.html` + `styles.css`) — the LLM never emits HTML. Registry: `app/services/resume_render.py` (`classic` → `classic/v1` today).

All routes require `Authorization: Bearer <supabase_access_token>` (`DbUser`).

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/api/v1/resume/templates` | List `{id, name, version, description}` |
| `GET` | `/api/v1/resume/document` | Master remade profile as `ResumeDocument` |
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
