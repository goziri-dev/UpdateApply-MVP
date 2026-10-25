"""Shared ATS board catalog (Phase 1). No user id — ingest is global."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

# greenhouse | lever | ashby
VENDOR_VALUES = ("greenhouse", "lever", "ashby")
# active | unavailable | disabled
BOARD_STATUS_VALUES = ("active", "unavailable", "disabled")
# seed | user
BOARD_SOURCE_VALUES = ("seed", "user")


class CompanyBoard(SQLModel, table=True):
    """One public ATS board. Unique on ``(vendor, slug)``."""

    # pyrefly: ignore[bad-override]
    __tablename__ = "company_board"
    __table_args__ = (
        UniqueConstraint("vendor", "slug", name="uq_company_board_vendor_slug"),
        CheckConstraint(
            "vendor IN ('greenhouse', 'lever', 'ashby')",
            name="ck_company_board_vendor",
        ),
        CheckConstraint(
            "status IN ('active', 'unavailable', 'disabled')",
            name="ck_company_board_status",
        ),
        CheckConstraint(
            "source IN ('seed', 'user')",
            name="ck_company_board_source",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    vendor: str = Field(max_length=32, index=True)
    slug: str = Field(max_length=256, index=True)
    company_name: str = Field(max_length=512)
    # active | unavailable | disabled
    status: str = Field(default="active", max_length=32, index=True)
    # seed | user
    source: str = Field(default="seed", max_length=32)
    last_fetched_at: datetime | None = Field(default=None)
    last_error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    consecutive_failures: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
