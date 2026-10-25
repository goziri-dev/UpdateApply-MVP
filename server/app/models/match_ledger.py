"""Per-user match ledger for Jobs For You (Phase 2). Not an Applications row."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class MatchLedger(SQLModel, table=True):
    """One score/reason row per (user, posting). Tracks opened / notified."""

    # pyrefly: ignore[bad-override]
    __tablename__ = "match_ledger"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "posting_id",
            name="uq_match_ledger_user_posting",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    posting_id: UUID = Field(foreign_key="job_posting.id", index=True)
    score: float | None = Field(default=None)
    reason: str = Field(default="", sa_column=Column(Text, nullable=False))
    matched_title: str | None = Field(default=None, max_length=512)
    notified_at: datetime | None = Field(default=None)
    opened_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
