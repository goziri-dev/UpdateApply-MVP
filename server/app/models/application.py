from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Application(SQLModel, table=True):
    """One tailored resume version for a job (never upserted on company+role)."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    company: str = Field(default="", index=True)
    target_role: str = Field(default="", index=True)
    job_description: str = Field(default="", sa_column=Column(Text, nullable=False))
    # Full ResumeDocument JSON — PDFs are regenerated on demand, not stored.
    resume_document: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )
    # draft | applied (extensible later; not a full ATS pipeline)
    status: str = Field(default="draft", index=True)
    # Stable display version for this company+role lineage (1, 2, …).
    version: int = Field(default=1)
    applied_at: datetime | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
