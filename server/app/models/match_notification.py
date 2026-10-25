"""In-app notification log for strong job matches (Phase 3)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class MatchNotification(SQLModel, table=True):
    """One delivered notify event per (user, posting). Channel = in-app log."""

    # pyrefly: ignore[bad-override]
    __tablename__ = "match_notification"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "posting_id",
            name="uq_match_notification_user_posting",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    posting_id: UUID = Field(foreign_key="job_posting.id", index=True)
    title: str = Field(max_length=512)
    company: str = Field(max_length=512)
    reason: str = Field(default="", sa_column=Column(Text, nullable=False))
    score: float | None = Field(default=None)
    channel: str = Field(default="in_app", max_length=32)
    read_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
