from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class WaitlistSignup(SQLModel, table=True):
    """Marketing waitlist capture — does not grant app access."""

    # pyrefly: ignore[bad-override]
    __tablename__ = "waitlist_signup"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=254)
    name: str | None = Field(default=None, max_length=120)
    career_stage: str | None = Field(default=None, max_length=32)
    job_search_challenges: str | None = Field(default=None, max_length=1000)
    source: str | None = Field(default=None, max_length=64)
    ip: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=512)
    # pending | approved | rejected — Favour review; approve ≠ auto-session
    status: str = Field(default="pending", index=True, max_length=32)
    reviewed_at: datetime | None = Field(default=None)
    reviewed_by: str | None = Field(default=None, max_length=128)
    review_note: str | None = Field(default=None, max_length=512)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
