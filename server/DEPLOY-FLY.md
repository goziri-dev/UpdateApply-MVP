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

## Stripe billing (TSK-64)

Direct Stripe Checkout + webhooks (not RevenueCat). Secrets only — never bake keys into the image.

```bash
# Prefer test-mode secrets until go-live. Mirror live Products/Prices in test mode first.
fly secrets set \
  STRIPE_SECRET_KEY='sk_test_…' \
  STRIPE_WEBHOOK_SECRET='whsec_…' \
  STRIPE_PUBLISHABLE_KEY='pk_test_…' \
  STRIPE_PRICE_PAYG='price_…' \
  STRIPE_PRICE_LITE='price_…' \
  STRIPE_PRICE_PLUS='price_…' \
  STRIPE_CHECKOUT_SUCCESS_URL='https://app.updateapply.com/credits?billing=success&session_id={CHECKOUT_SESSION_ID}' \
  STRIPE_CHECKOUT_CANCEL_URL='https://app.updateapply.com/credits?billing=cancel' \
  STRIPE_PORTAL_RETURN_URL='https://app.updateapply.com/credits'
```

**Catalog (acct_1Tj0MGLpMjkUpLaG):**

| Plan | Test price | Live price |
|------|------------|------------|
| PAYG €2.99 | `price_1UX0R9LpMjkUpLaGnh0P5Tht` | `price_1UX0EFLpMjkUpLaGaa4QK4rn` |
| Lite €9.99/mo | `price_1UX0R8LpMjkUpLaGeg1iKmwd` | `price_1UX0EGLpMjkUpLaG8LO0kTOT` |
| Plus €14.99/mo | `price_1UX0R9LpMjkUpLaGFcSGRgAv` | `price_1UX0EHLpMjkUpLaGo7LWuG7I` |

Settings / local defaults use **test** price IDs. On Fly with `sk_test_*`, you can omit price secrets (defaults work) or set them explicitly.

**Dashboard (Favour):**

1. Customer Portal: Settings → Billing → Customer portal (activate; allow cancel/switch as desired).
2. Webhooks → endpoint `https://api.updateapply.com/api/v1/billing/webhook` — events `checkout.session.completed`, `invoice.paid`. Copy signing secret → `STRIPE_WEBHOOK_SECRET`. Local: `stripe listen --forward-to localhost:8000/api/v1/billing/webhook`.
3. Live go-live: swap to `sk_live_…` + live price IDs above + live webhook secret. Never mix `sk_test` with live prices.

API surface: `GET /api/v1/billing/balance`, `POST /api/v1/billing/checkout` `{plan: payg|lite|plus}`, `POST /api/v1/billing/portal`, `POST /api/v1/billing/webhook`. Successful `POST /api/v1/tailor` deducts 1 credit (402 if empty). Free = 3 lifetime account grant.

## Flutter / Supabase

- Set the app’s API base URL to `https://api.updateapply.com` (Fly custom domain; `https://updateapply-mvp.fly.dev` still works).
- On **Vercel**, that is the project env var `API_BASE_URL` (build-time dart-define). After setting it, **Redeploy** — a prior bundle with `localhost:8000` will keep failing until rebuilt. See `app/README.md` → Vercel.
- Add Flutter web origins to `CORS_ORIGINS` (must include `https://app.updateapply.com`).
- Supabase Auth redirect URLs / site URL must allow `https://app.updateapply.com`; JWT verification still uses the secrets above.
