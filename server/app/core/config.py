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


@lru_cache
def get_settings() -> Settings:
    return Settings()
