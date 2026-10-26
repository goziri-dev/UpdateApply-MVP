#!/usr/bin/env bash
# One-shot: deploy FastAPI waitlist + Next.js landing, move apex/www.
# Run from repo root in a normal Terminal (not sandboxed agent shell).
# Does not print secret values.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$ROOT/.tmp-xdg-data}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$ROOT/.tmp-xdg-cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$ROOT/.tmp-xdg-config}"
export PATH="$HOME/.fly/bin:$PATH"

TEAM="${VERCEL_TEAM:-goziris-projects}"
LANDING_PROJECT="${LANDING_PROJECT:-updateapply-landing}"
APP_PROJECT="${APP_PROJECT:-updateapply-mvp-app}"

echo "==> 1) Fly deploy API (waitlist POST /api/v1/waitlist)"
cd "$ROOT/server"
fly deploy -a updateapply-mvp --ha=false

echo "==> 2) Smoke waitlist API"
curl -sS -m 20 -X POST 'https://api.updateapply.com/api/v1/waitlist' \
  -H 'content-type: application/json' \
  -d '{"email":"waitlist-api-smoke-20261026@updateapply.com","source":"landing"}'
echo
curl -sS -m 20 -X POST 'https://api.updateapply.com/api/v1/waitlist' \
  -H 'content-type: application/json' \
  -d '{"email":"Waitlist-Api-Smoke-20261026@UpdateApply.com","source":"landing"}'
echo

echo "==> 3) Link / create Vercel project for landing/"
cd "$ROOT/landing"
bunx vercel link --yes --scope "$TEAM" --project "$LANDING_PROJECT" || \
  bunx vercel project add "$LANDING_PROJECT" --scope "$TEAM"

echo "==> 4) Set landing env (edit service role if prompted)"
# Public
bunx vercel env add NEXT_PUBLIC_SITE_URL production --scope "$TEAM" --force <<'EOF' || true
https://updateapply.com
EOF
bunx vercel env add NEXT_PUBLIC_APP_URL production --scope "$TEAM" --force <<'EOF' || true
https://app.updateapply.com
EOF
# Prefer FastAPI once deployed; Supabase service role is the durable fallback.
bunx vercel env add WAITLIST_API_URL production --scope "$TEAM" --force <<'EOF' || true
https://api.updateapply.com/api/v1/waitlist
EOF
bunx vercel env add SUPABASE_URL production --scope "$TEAM" --force <<'EOF' || true
https://ecwdwrvjbmdgdeioivfw.supabase.co
EOF
echo "Set SUPABASE_SERVICE_ROLE_KEY in Vercel dashboard (server-only) if WAITLIST_API_URL fails."

echo "==> 5) Deploy landing production"
bunx vercel --prod --yes --scope "$TEAM"

echo "==> 6) Domain cutover (interactive if DNS needed)"
echo "Attach apex + www to $LANDING_PROJECT; remove from $APP_PROJECT (keep app.)"
bunx vercel domains add updateapply.com --scope "$TEAM" 2>/dev/null || true
bunx vercel domains add www.updateapply.com --scope "$TEAM" 2>/dev/null || true
# Prefer assigning to landing project via dashboard if CLI project binding is unclear.
echo "In Vercel: $LANDING_PROJECT → Domains → add updateapply.com + www"
echo "In Vercel: $APP_PROJECT → Domains → remove updateapply.com + www (keep app.updateapply.com)"
echo "Namecheap: follow Vercel DNS instructions for apex (A/ALIAS) and www (CNAME)."

echo "==> Done. Smoke: https://updateapply.com  and waitlist form."
