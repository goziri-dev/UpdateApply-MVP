"""Local posting store from ATS list ingest (Phase 1)."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, Column, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.profile_chunk import EMBEDDING_DIMENSIONS

# greenhouse | lever | ashby
VENDOR_VALUES = ("greenhouse", "lever", "ashby")


class JobPosting(SQLModel, table=True):
    """One job we have seen on a public board. Unique on ``(vendor, external_job_id)``."""

    # pyrefly: ignore[bad-override]
    __tablename__ = "job_posting"
    __table_args__ = (
        UniqueConstraint(
            "vendor",
            "external_job_id",
            name="uq_job_posting_vendor_external_job_id",
        ),
        CheckConstraint(
            "vendor IN ('greenhouse', 'lever', 'ashby')",
            name="ck_job_posting_vendor",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    board_id: UUID = Field(foreign_key="company_board.id", index=True)
    vendor: str = Field(max_length=32, index=True)
    external_job_id: str = Field(max_length=256, index=True)
    company_name: str = Field(default="", max_length=512)
    title: str = Field(default="", max_length=1024)
    location_raw: str = Field(default="", sa_column=Column(Text, nullable=False))
    # Filled by Phase 2 normalization — nullable until then.
    location_remote: bool | None = Field(default=None)
    location_countries: list[str] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    location_parse_status: str | None = Field(default=None, max_length=32)
    description_text: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    description_truncated: bool = Field(default=False)
    apply_url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    vendor_posted_at: datetime | None = Field(default=None)
    vendor_updated_at: datetime | None = Field(default=None)
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str | None = Field(default=None, max_length=64)
    # Null until description is stored / re-embedded (Phase 2).
    embedding: Any = Field(
        default=None,
        sa_column=Column(Vector(EMBEDDING_DIMENSIONS), nullable=True),
    )
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
