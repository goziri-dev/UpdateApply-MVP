#!/usr/bin/env bash
# Vercel build for Flutter web. Keep the Vercel "Build Command" short (≤256 chars).
# Expected Vercel Root Directory: app
# Preferred Build Command: bash vercel-build.sh  (works even if +x is lost)
# Env (Vercel project): SUPABASE_URL, SUPABASE_ANON_KEY
# Optional: API_BASE_URL (defaults to Fly prod if missing/localhost), SUPABASE_AUTH_REDIRECT_URL
set -euo pipefail

cd "$(dirname "$0")"

trim_env() {
  # Strip surrounding whitespace and matching single/double quotes (common
  # when pasting into the Vercel dashboard).
  local value="${1:-}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  if [[ "${value}" == \"*\" && "${value}" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "${value}" == \'*\' && "${value}" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "${value}"
}

# Production API host for this MVP. If Vercel still has localhost from a copied
# .env, remap instead of failing the build — otherwise Redeploy loops forever.
DEFAULT_API_BASE_URL="https://api.updateapply.com"

normalize_api_base_url() {
  local value
  value="$(trim_env "${API_BASE_URL:-}")"
  case "${value}" in
    ""|http://localhost*|http://127.0.0.1*|https://localhost*|https://127.0.0.1*)
      echo "warning: API_BASE_URL missing or localhost (${value:-empty}); using ${DEFAULT_API_BASE_URL}" >&2
      API_BASE_URL="${DEFAULT_API_BASE_URL}"
      ;;
    http://*|https://*)
      API_BASE_URL="${value}"
      ;;
    *)
      echo "error: API_BASE_URL must be an http(s) URL (got: ${value})." >&2
      echo "  Set API_BASE_URL=${DEFAULT_API_BASE_URL} in Vercel → Settings → Environment Variables." >&2
      exit 1
      ;;
  esac
}

require_nonempty() {
  local name="$1"
  local value
  value="$(trim_env "${!1:-}")"
  if [[ -z "${value}" ]]; then
    echo "error: ${name} is required in Vercel env (Production + Preview)." >&2
    exit 1
  fi
  printf -v "${name}" '%s' "${value}"
}

normalize_api_base_url
require_nonempty SUPABASE_URL
require_nonempty SUPABASE_ANON_KEY
if [[ -n "${SUPABASE_AUTH_REDIRECT_URL:-}" ]]; then
  SUPABASE_AUTH_REDIRECT_URL="$(trim_env "${SUPABASE_AUTH_REDIRECT_URL}")"
fi

FLUTTER_DIR="${HOME}/flutter"
if [[ ! -d "${FLUTTER_DIR}/bin" ]]; then
  echo "Cloning Flutter stable into ${FLUTTER_DIR}..."
  rm -rf "${FLUTTER_DIR}"
  git clone --depth 1 -b stable https://github.com/flutter/flutter.git "${FLUTTER_DIR}"
fi

export PATH="${FLUTTER_DIR}/bin:${PATH}"
# Avoid interactive prompts / analytics on CI images.
flutter config --no-analytics --enable-web >/dev/null

echo "flutter $(flutter --version 2>/dev/null | head -1 || echo unknown)"
flutter pub get

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
