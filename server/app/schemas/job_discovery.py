"""Wire shapes for Match Preferences + Jobs For You (Phase 0)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

RemotePreference = Literal["remote_only", "remote_ok", "onsite_only"]

SeniorityBand = Literal[
    "intern",
    "junior",
    "mid",
    "senior",
    "staff_principal",
    "lead_manager",
]

EmptyReason = Literal["no_preferences", "no_matches"]


class TitleSuggestion(BaseModel):
    title: str
    reason: str


class TitleSuggestionsResponse(BaseModel):
    suggestions: list[TitleSuggestion]


class MatchPreferencesRead(BaseModel):
    id: UUID
    user_id: UUID
    titles: list[str]
    seniority_bands: list[str]
    remote_preference: RemotePreference
    countries: list[str]
    city: str | None = None
    confirmed_at: datetime
    updated_at: datetime


class MatchPreferencesGetResponse(BaseModel):
    """Always 200 — ``preferences`` is null when the user has not saved yet."""

    preferences: MatchPreferencesRead | None = None


class MatchPreferencesUpsert(BaseModel):
    titles: list[str] = Field(min_length=1)
    seniority_bands: list[SeniorityBand] = Field(min_length=1)
    remote_preference: RemotePreference
    countries: list[str] = Field(default_factory=list)
    city: str | None = None


class JobsForYouItem(BaseModel):
    """Ranked shortlist row from job_posting + match ledger (Phase 2)."""

    posting_id: UUID
    title: str
    company: str
    location_raw: str
    apply_url: str | None = None
    score: float | None = None
    reason: str
    matched_title: str | None = None
    # Stored description for tailor prefill (not a live ATS fetch).
    description_text: str | None = None


class JobsForYouResponse(BaseModel):
    items: list[JobsForYouItem]
    empty_reason: EmptyReason | None = None
    cap: int
    cap_is_default: bool = True


class JobsForYouOpenResponse(BaseModel):
    posting_id: UUID
    opened_at: datetime


class CareersUrlRequest(BaseModel):
    url: str = Field(min_length=1)


class CareersUrlResponse(BaseModel):
    vendor: str
    slug: str
    company_name: str
    status: str
    source: str
    created: bool
    reactivated: bool
    message: str


class MatchNotificationItem(BaseModel):
    id: UUID
    posting_id: UUID
    title: str
    company: str
    reason: str
    score: float | None = None
    channel: str
    read_at: datetime | None = None
    created_at: datetime


class MatchNotificationsResponse(BaseModel):
    items: list[MatchNotificationItem]
    unread_count: int
