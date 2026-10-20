from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """Local app user row. Primary key matches Supabase Auth ``sub`` (UUID)."""

    id: UUID = Field(primary_key=True)
    email: str | None = Field(default=None, index=True)
    display_name: str | None = None
    # e.g. "google", "github", "notion" — from JWT app_metadata when present
    oauth_provider: str | None = Field(default=None, index=True)
    # Same as str(id); kept for unique lookups / future multi-provider links
    oauth_subject: str = Field(index=True, unique=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
