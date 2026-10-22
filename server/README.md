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

## OpenRouter

`AgentFactory` sets a **60s** request timeout on every chat client. Without that, a stalled provider can hang sync `/parse` indefinitely (Flutter looks “frozen”).

Task → default model: see `app/core/llm_tasks.py`. Override with `OPENROUTER_MODEL_*` env vars when needed.

Interview mic STT uses OpenRouter `POST /api/v1/audio/transcriptions` (default `openai/whisper-1`). Override with `OPENROUTER_MODEL_INTERVIEW_TRANSCRIBE`. Audio is transcribed in memory and not stored. Endpoint: `POST /api/v1/onboarding/interview/transcribe`.

## Auth

JWT verify order: JWKS → HS256 (`SUPABASE_JWT_SECRET`) → Auth `get_user` fallback. Requires `SUPABASE_URL` + `SUPABASE_ANON_KEY`.
