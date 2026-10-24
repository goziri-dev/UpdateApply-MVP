"""Per-user Match Preferences for Jobs For You (Phase 0).

Target scope Decision for this slice: **per user** (one active set per
``user_id``). Global deployment targets were rejected for personalized matching.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class MatchPreference(SQLModel, table=True):
    """Confirmed titles, place, and seniority for one user.

    Suggestions are never stored here — only what the user saved.
    """

    # pyrefly: ignore[bad-override]
    __tablename__ = "match_preference"
    __table_args__ = (UniqueConstraint("user_id", name="uq_match_preference_user_id"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    # Confirmed hiring-title strings (exact filter phrases).
    titles: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    # Allowed bands: intern | junior | mid | senior | staff_principal | lead_manager
    seniority_bands: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    # remote_only | remote_ok | onsite_only
    remote_preference: str = Field(default="remote_ok", max_length=32)
    countries: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    city: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    confirmed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Keep typing happy for JSONB list fields when reading raw rows.
    def as_public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "titles": list(self.titles or []),
            "seniority_bands": list(self.seniority_bands or []),
            "remote_preference": self.remote_preference,
            "countries": list(self.countries or []),
            "city": self.city,
            "confirmed_at": self.confirmed_at,
            "updated_at": self.updated_at,
        }
