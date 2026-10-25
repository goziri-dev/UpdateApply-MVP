# Deploy UpdateApply API to Fly.io

Artifacts live in this directory (`Dockerfile`, `fly.toml`, `.dockerignore`). Do not bake secrets into the image — use `fly secrets set`.

## After account signup

```bash
# Install CLI if needed: https://fly.io/docs/hands-on/install-flyctl/
fly auth login

cd server

# Create the app (or: fly launch --no-deploy and accept/edit fly.toml)
fly apps create updateapply-api
# Optional: fly regions set iad   # match primary_region in fly.toml

# Required secrets (from .env.example — use your real values)
fly secrets set \
  DATABASE_URL='postgresql+psycopg://…' \
  SUPABASE_URL='https://….supabase.co' \
  SUPABASE_ANON_KEY='…' \
  SUPABASE_SERVICE_ROLE_KEY='…' \
  SUPABASE_JWT_SECRET='…' \
  OPENROUTER_API_KEY='…' \
  CORS_ORIGINS='https://your-flutter-web-origin,http://localhost:5000'

# Optional
# fly secrets set TAVILY_API_KEY='…' NOTIFY_WEBHOOK_URL='…'

fly deploy
```

App URL: `https://updateapply-api.fly.dev` (or your custom domain).

## Local smoke-test (no Fly account)

```bash
cd server
docker build -t updateapply-api .
docker run --rm -p 8000:8000 --env-file .env updateapply-api
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

## Flutter / Supabase

- Set the app’s API base URL to the Fly hostname.
- Add that origin (and any Flutter web origins) to `CORS_ORIGINS`.
- Supabase Auth redirect URLs / site URL must allow your Flutter clients; JWT verification still uses the secrets above.
