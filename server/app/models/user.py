from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """OAuth-backed account. Provider wiring is stubbed in auth router."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str | None = Field(default=None, index=True)
    display_name: str | None = None
    # e.g. "google", "github", "notion"
    oauth_provider: str | None = Field(default=None, index=True)
    oauth_subject: str | None = Field(default=None, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
