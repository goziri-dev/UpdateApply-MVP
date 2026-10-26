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

: "${API_BASE_URL:?API_BASE_URL is required}"
: "${SUPABASE_URL:?SUPABASE_URL is required}"
: "${SUPABASE_ANON_KEY:?SUPABASE_ANON_KEY is required}"

DEFINES=(
  "--dart-define=API_BASE_URL=${API_BASE_URL}"
  "--dart-define=SUPABASE_URL=${SUPABASE_URL}"
  "--dart-define=SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}"
)
if [[ -n "${SUPABASE_AUTH_REDIRECT_URL:-}" ]]; then
  DEFINES+=("--dart-define=SUPABASE_AUTH_REDIRECT_URL=${SUPABASE_AUTH_REDIRECT_URL}")
fi

flutter build web --release "${DEFINES[@]}"
