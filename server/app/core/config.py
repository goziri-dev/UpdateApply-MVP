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
    notify_daily_cap: int = 3
    notify_similarity_floor: float = 0.35
    # Optional outbound webhook (Slack/email bridge). Empty → in-app log only.
    notify_webhook_url: str = ""
    notify_webhook_timeout_seconds: float = 10.0

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

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
