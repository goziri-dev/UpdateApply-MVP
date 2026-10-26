#!/usr/bin/env bash
# Vercel build for Flutter web. Keep the Vercel "Build Command" short (≤256 chars).
# Expected Vercel Root Directory: app
# Env (Vercel project): API_BASE_URL, SUPABASE_URL, SUPABASE_ANON_KEY
# Optional: SUPABASE_AUTH_REDIRECT_URL
set -euo pipefail

cd "$(dirname "$0")"

FLUTTER_DIR="${HOME}/flutter"
if [[ ! -d "${FLUTTER_DIR}/bin" ]]; then
  rm -rf "${FLUTTER_DIR}"
  git clone https://github.com/flutter/flutter.git --depth 1 -b stable "${FLUTTER_DIR}"
fi

export PATH="${FLUTTER_DIR}/bin:${PATH}"

flutter config --no-analytics
flutter pub get

# Compile-time dart-defines. Missing API_BASE_URL silently falls back to
# http://localhost:8000 in AppEnv — which breaks production (HTTPS page →
# localhost). Fail the Vercel build instead of shipping a useless bundle.
require_https_public_url() {
  local name="$1"
  local value="${!1:-}"
  if [[ -z "${value}" ]]; then
    echo "error: ${name} is required in Vercel env (Production + Preview)." >&2
    echo "  Set ${name}=https://updateapply-mvp.fly.dev then Redeploy." >&2
    exit 1
  fi
  case "${value}" in
    http://localhost*|http://127.0.0.1*|https://localhost*|https://127.0.0.1*)
      echo "error: ${name} must be the public API URL, not localhost (${value})." >&2
      echo "  Set ${name}=https://updateapply-mvp.fly.dev then Redeploy." >&2
      exit 1
      ;;
    http://*|https://*) ;;
    *)
      echo "error: ${name} must be an http(s) URL (got: ${value})." >&2
      exit 1
      ;;
  esac
}

require_https_public_url API_BASE_URL
: "${SUPABASE_URL:?SUPABASE_URL is required in Vercel env}"
: "${SUPABASE_ANON_KEY:?SUPABASE_ANON_KEY is required in Vercel env}"

echo "Building Flutter web with API_BASE_URL=${API_BASE_URL}"

DEFINES=(
  "--dart-define=API_BASE_URL=${API_BASE_URL}"
  "--dart-define=SUPABASE_URL=${SUPABASE_URL}"
  "--dart-define=SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}"
)
if [[ -n "${SUPABASE_AUTH_REDIRECT_URL:-}" ]]; then
  DEFINES+=("--dart-define=SUPABASE_AUTH_REDIRECT_URL=${SUPABASE_AUTH_REDIRECT_URL}")
fi

flutter build web --release "${DEFINES[@]}"
