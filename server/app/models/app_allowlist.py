from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class AppAllowlist(SQLModel, table=True):
    """Emails allowed to use the app after Supabase auth. Soft-revoke via revoked_at."""

    # pyrefly: ignore[bad-override]
    __tablename__ = "app_allowlist"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=254)
    user_id: UUID | None = Field(default=None, index=True)
    note: str | None = Field(default=None, max_length=512)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str | None = Field(default=None, max_length=128)
    revoked_at: datetime | None = Field(default=None)
