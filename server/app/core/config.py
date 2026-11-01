from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_UNIT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_UNIT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "UpdateApply"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    openrouter_api_key: str = ""
    # Legacy / fallback default. Prefer AgentTask defaults + per-task overrides.
    openrouter_model: str = "google/gemini-2.5-flash"
    # Optional OpenRouter model overrides (empty → DEFAULT_MODEL_BY_TASK).
    openrouter_model_resume_extract: str = ""
    openrouter_model_interview_questions: str = ""
    openrouter_model_profile_review: str = ""
    openrouter_model_resume_tailor: str = ""
    openrouter_model_resume_edit: str = ""
    openrouter_model_title_suggestions: str = ""
    # Embeddings for pgvector RAG (OpenRouter /embeddings). Empty → text-embedding-3-small.
    openrouter_model_embedding: str = ""
    # STT for interview mic (OpenRouter /audio/transcriptions). Empty → whisper-1.
    openrouter_model_interview_transcribe: str = ""

    # Optional Tavily key for resume Ask mode (live web search). Empty → clear error.
    tavily_api_key: str = ""

    # Local resume PDF storage (one file per user). Relative paths resolve from unit root.
    resume_upload_dir: str = str(_UNIT_ROOT / "data" / "uploads")
    # Offline click-through only. When false (default), parse never returns demo data.
    allow_stub_parse: bool = False

    # ATS ingest (Phase 1) — per-host politeness; no user id involved.
    # Pause between HTTP calls to the same host (seconds).
    ingest_host_pause_seconds: float = 0.75
    # Non-404 failures before quarantining a board as unavailable.
    ingest_failure_threshold: int = 3
    # Plain-text JD body cap; longer bodies set description_truncated=true.
    ingest_description_max_chars: int = 50_000
    # HTTP timeout for ATS list/detail requests (seconds).
    ingest_http_timeout_seconds: float = 30.0

    # Phase 3 — daily run + notify (Decision: cap 3, floor 0.35, in-app + optional webhook).
    # Prefer OS cron → ``uv run updateapply-catalog daily``. In-process runner is optional.
    enable_daily_job_runner: bool = False
    daily_job_runner_hour_utc: int = 6
    # Jobs For You Pass-1 freshness window (hours). Stale catalogs auto-widen
    # up to 14 days via job_match.effective_lookback_hours.
    job_match_lookback_hours: int = 48
    notify_daily_cap: int = 3
    notify_similarity_floor: float = 0.35
    # Optional outbound webhook (Slack/email bridge). Empty → in-app log only.
    notify_webhook_url: str = ""
    notify_webhook_timeout_seconds: float = 10.0

    # LLM route rate limits (process-local sliding window; see app.core.rate_limit).
    # Heavy: parse, tailor, review generate, deepen propose.
    # Standard: edit, deepen turns, interview/STT, title suggestions.
    # Set a limit to 0 to disable that tier (tests / emergency).
    llm_rate_limit_heavy: int = 10
    llm_rate_window_seconds_heavy: int = 600
    llm_rate_limit_standard: int = 40
    llm_rate_window_seconds_standard: int = 600

    # Admin API (waitlist list/approve/reject + allowlist CRUD). Header: X-Admin-Key.
    admin_api_key: str = ""

    # Resend transactional email (waitlist notify Favour + optional "you're in").
    # Empty RESEND_API_KEY → notify is logged/stubbed; signup still succeeds.
    resend_api_key: str = ""
    resend_from_email: str = "UpdateApply <noreply@updateapply.com>"
    admin_notify_email: str = ""
    app_public_url: str = "https://app.updateapply.com"
    # Public API base for signed waitlist Approve/Reject email links.
    api_public_url: str = "https://api.updateapply.com"
    # Optional Slack/Discord webhook for new waitlist signups (in addition to Resend).
    waitlist_notify_webhook_url: str = ""

    # Waitlist → Google Sheet sync via Composio (best-effort; empty → skip).
    waitlist_google_sheet_id: str = ""
    waitlist_google_sheet_range: str = "Sheet1!A:H"
    composio_api_key: str = ""
    composio_google_sheets_account_id: str = ""
    composio_user_id: str = ""

    # Sentry error + performance monitoring (empty DSN → SDK not initialized).
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    # Prefer Fly image/release tag or git SHA in production.
    sentry_release: str = ""
    # Traces: 1.0 locally; 0.1 on Fly. /health is always dropped by traces_sampler.
    sentry_traces_sample_rate: float = 1.0
    # Profiles attach to sampled traces (profile_lifecycle=trace in init).
    sentry_profile_session_sample_rate: float = 1.0
    # Temporary ZeroDivisionError route for Sentry smoke tests. Keep false in prod.
    sentry_enable_debug_route: bool = False

    # --- Stripe (direct Checkout + webhooks; not RevenueCat) ---
    # Empty secret key → billing routes return 503 (safe local default).
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    # Publishable key is for Flutter / client; documented in .env.example only.
    stripe_publishable_key: str = ""
    # Price IDs must match the secret key mode (sk_test ↔ test prices).
    # Defaults = test-mode mirrors (acct_1Tj0MGLpMjkUpLaG, livemode=false).
    # Live (go-live only): PAYG price_1UX0EFLpMjkUpLaGaa4QK4rn,
    # Lite price_1UX0EGLpMjkUpLaG8LO0kTOT, Plus price_1UX0EHLpMjkUpLaGo7LWuG7I.
    stripe_price_payg: str = "price_1UX0R9LpMjkUpLaGnh0P5Tht"
    stripe_price_lite: str = "price_1UX0R8LpMjkUpLaGeg1iKmwd"
    stripe_price_plus: str = "price_1UX0R9LpMjkUpLaGFcSGRgAv"
    # Credits granted per product (must match Stripe product metadata / Decision).
    stripe_credits_payg: int = 1
    stripe_credits_lite: int = 10
    stripe_credits_plus: int = 25
    # Lifetime free account grant (not a Stripe Product).
    stripe_free_credits: int = 3
    # Checkout return URLs (Flutter web). Empty → derived from APP_PUBLIC_URL.
    # {CHECKOUT_SESSION_ID} is a Stripe placeholder — leave it literal.
    stripe_checkout_success_url: str = ""
    stripe_checkout_cancel_url: str = ""
    stripe_portal_return_url: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def stripe_secret_is_live(self) -> bool:
        return self.stripe_secret_key.strip().startswith("sk_live_")

    @property
    def stripe_secret_is_test(self) -> bool:
        return self.stripe_secret_key.strip().startswith("sk_test_")

    @property
    def stripe_prices_look_test_default(self) -> bool:
        """True when all three prices match the baked-in test-mode IDs."""
        return (
            self.stripe_price_payg.strip() == "price_1UX0R9LpMjkUpLaGnh0P5Tht"
            and self.stripe_price_lite.strip() == "price_1UX0R8LpMjkUpLaGeg1iKmwd"
            and self.stripe_price_plus.strip() == "price_1UX0R9LpMjkUpLaGFcSGRgAv"
        )

    @property
    def stripe_mode_mismatch(self) -> str | None:
        """Human warning when sk_live is paired with test price defaults (or reverse)."""
        if not self.stripe_configured:
            return None
        if self.stripe_secret_is_live and self.stripe_prices_look_test_default:
            return (
                "STRIPE_SECRET_KEY is sk_live_* but price IDs are the test-mode "
                "defaults. Switch to sk_test_* for local smoke, or set "
                "STRIPE_PRICE_* to the live price IDs."
            )
        if self.stripe_secret_is_test and not self.stripe_prices_look_test_default:
            # Not necessarily wrong (custom test prices), so soft note only when
            # prices match the known live IDs.
            live = {
                "price_1UX0EFLpMjkUpLaGaa4QK4rn",
                "price_1UX0EGLpMjkUpLaG8LO0kTOT",
                "price_1UX0EHLpMjkUpLaGo7LWuG7I",
            }
            configured = {
                self.stripe_price_payg.strip(),
                self.stripe_price_lite.strip(),
                self.stripe_price_plus.strip(),
            }
            if configured <= live:
                return (
                    "STRIPE_SECRET_KEY is sk_test_* but STRIPE_PRICE_* look like "
                    "live IDs. Use the test price IDs from .env.example."
                )
        return None

    def resolved_checkout_success_url(self) -> str:
        if self.stripe_checkout_success_url.strip():
            return self.stripe_checkout_success_url.strip()
        base = self.app_public_url.rstrip("/")
        return f"{base}/credits?billing=success&session_id={{CHECKOUT_SESSION_ID}}"

    def resolved_checkout_cancel_url(self) -> str:
        if self.stripe_checkout_cancel_url.strip():
            return self.stripe_checkout_cancel_url.strip()
        return f"{self.app_public_url.rstrip('/')}/credits?billing=cancel"

    def resolved_portal_return_url(self) -> str:
        if self.stripe_portal_return_url.strip():
            return self.stripe_portal_return_url.strip()
        return f"{self.app_public_url.rstrip('/')}/credits"

    @property
    def supabase_configured(self) -> bool:
        """Client credentials present (JWT secret optional when JWKS is enabled)."""
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def openrouter_configured(self) -> bool:
        return bool(self.openrouter_api_key.strip())

    @property
    def admin_configured(self) -> bool:
        return bool(self.admin_api_key.strip())

    @property
    def resend_configured(self) -> bool:
        return bool(self.resend_api_key.strip() and self.admin_notify_email.strip())

    @property
    def stripe_configured(self) -> bool:
        return bool(self.stripe_secret_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
