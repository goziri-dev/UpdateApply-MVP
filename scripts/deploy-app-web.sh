#!/usr/bin/env bash
# Deploy Flutter web to Vercel project updateapply-mvp-app.
#
# CRITICAL: run this from the monorepo (script does it). The Vercel project
# Root Directory is `app`. If you `cd app && vercel --prod`, Vercel looks for
# `app/app` inside the upload and fails with:
#   The specified Root Directory "app" does not exist.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEAM="${VERCEL_TEAM:-goziris-projects}"
PROJECT="${APP_PROJECT:-updateapply-mvp-app}"

if [[ "$(basename "$PWD")" == "app" ]]; then
  echo "error: do not deploy from app/. Use: bash scripts/deploy-app-web.sh" >&2
  exit 1
fi

cd "$ROOT"
echo "==> Link monorepo root → $PROJECT (Root Directory must stay 'app' in dashboard)"
bunx vercel link --yes --scope "$TEAM" --project "$PROJECT"

echo "==> Deploy production from monorepo root"
bunx vercel --prod --yes --scope "$TEAM"

echo "==> Done. Smoke: https://app.updateapply.com"
