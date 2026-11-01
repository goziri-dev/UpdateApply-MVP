# Deploy UpdateApply API to Fly.io

Artifacts live in this directory (`Dockerfile`, `fly.toml`, `.dockerignore`). Do not bake secrets into the image — use `fly secrets set`.

## After account signup

```bash
# Install CLI if needed: https://fly.io/docs/hands-on/install-flyctl/
fly auth login

cd server

# Create the app (or: fly launch --no-deploy and accept/edit fly.toml)
fly apps create updateapply-mvp
# Optional: fly regions set iad   # match primary_region in fly.toml

# Required secrets (from .env.example — use your real values)
fly secrets set \
  DATABASE_URL='postgresql+psycopg://…' \
  SUPABASE_URL='https://….supabase.co' \
  SUPABASE_ANON_KEY='…' \
  SUPABASE_SERVICE_ROLE_KEY='…' \
  SUPABASE_JWT_SECRET='…' \
  OPENROUTER_API_KEY='…' \
  CORS_ORIGINS='https://app.updateapply.com,https://www.updateapply.com,https://updateapply.com,http://localhost:5000'

# Optional
# fly secrets set TAVILY_API_KEY='…' NOTIFY_WEBHOOK_URL='…'

# Sentry (project updateapply-api — Client Keys DSN; do not bake into the image)
# fly secrets set \
#   SENTRY_DSN='…' \
#   SENTRY_ENVIRONMENT=production \
#   SENTRY_RELEASE="$(git rev-parse --short HEAD)" \
#   SENTRY_TRACES_SAMPLE_RATE=0.1 \
#   SENTRY_PROFILE_SESSION_SAMPLE_RATE=0.1
# Keep SENTRY_ENABLE_DEBUG_ROUTE unset/false on Fly (no public /sentry-debug).
#
# Verify Performance (latency) in Sentry UI:
# 1. Open https://goziri.sentry.io/insights/projects/updateapply-api/?project=updateapply-api
#    → Performance / Traces (or Explore → Traces).
# 2. Filter environment=production (or development for local).
# 3. Transaction names use URL path templates (e.g. POST /api/v1/tailor,
#    POST /api/v1/onboarding/parse). Child spans: ai.tailor / ai.parse.
# 4. Hit a real route (health is intentionally not sampled); wait ~1–2 min.

# Waitlist → Google Sheets (all five are required for sheet sync).
# Create the API key and Google Sheets connection in the same Composio
# Platform project; a Connect MCP account ID is not interchangeable.
fly secrets set \
  WAITLIST_GOOGLE_SHEET_ID='1h3SpdJP8Zk03uSb5SZPBJz2AVeS9qcneW_iBk16C2XQ' \
  WAITLIST_GOOGLE_SHEET_RANGE='Sheet1!A:H' \
  COMPOSIO_API_KEY='…' \
  COMPOSIO_GOOGLE_SHEETS_ACCOUNT_ID='…' \
  COMPOSIO_USER_ID='…'

fly deploy
```

App URL: `https://updateapply-mvp.fly.dev` (or your custom domain).

If the Machine is OOM-killed (`Process appears to have been OOM killed!`), bump RAM without waiting for a full redeploy: `fly scale memory 1024 -a updateapply-mvp` (or `512` as a floor).

## Local smoke-test (no Fly account)

```bash
cd server
docker build -t updateapply-mvp .
docker run --rm -p 8000:8000 --env-file .env updateapply-mvp
# curl -sS http://localhost:8000/health
```

Image CMD runs `uvicorn` without `--reload`. Migrations on Fly use `[deploy].release_command` (`alembic upgrade head`), not container start.

## Volumes (`data/uploads`)

Resume PDFs default to `/app/data/uploads`. Ephemeral filesystem is wiped on redeploy. For persistence:

```bash
fly volumes create updateapply_uploads --region iad --size 1
```

Uncomment `[[mounts]]` in `fly.toml`, then `fly deploy`.

## Daily catalog job

Prefer a separate cron (GitHub Actions, Fly Machines cron, or another host) calling:

```bash
uv run updateapply-catalog daily
```

In-process runner: `fly secrets set ENABLE_DAILY_JOB_RUNNER=true` (and optional `DAILY_JOB_RUNNER_HOUR_UTC`). File lock lives under `data/locks/` (ephemeral unless you mount a volume).

After deploy, seed/ingest once if the shared catalog is empty (`seed-boards`, `ingest`, etc. — see README).

## LLM rate limits (cost abuse)

Authenticated AI routes (parse / tailor / edit / deepen / interview / STT / title
suggestions) use process-local sliding windows (`LLM_RATE_LIMIT_*` in
`.env.example`). Defaults are fine on a single Machine; override via
`fly secrets set` if needed. Before scaling to multiple Machines/workers, swap
the in-memory limiter for Redis (or similar) — counters are per-process today.

## Flutter / Supabase

- Set the app’s API base URL to `https://api.updateapply.com` (Fly custom domain; `https://updateapply-mvp.fly.dev` still works).
- On **Vercel**, that is the project env var `API_BASE_URL` (build-time dart-define). After setting it, **Redeploy** — a prior bundle with `localhost:8000` will keep failing until rebuilt. See `app/README.md` → Vercel.
- Add Flutter web origins to `CORS_ORIGINS` (must include `https://app.updateapply.com`).
- Supabase Auth redirect URLs / site URL must allow `https://app.updateapply.com`; JWT verification still uses the secrets above.
