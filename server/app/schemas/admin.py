from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WaitlistAdminItem(BaseModel):
    id: UUID
    email: str
    name: str | None = None
    career_stage: str | None = None
    job_search_challenges: str | None = None
    source: str | None = None
    status: str
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    review_note: str | None = None


class WaitlistAdminListResponse(BaseModel):
    items: list[WaitlistAdminItem]


class WaitlistReviewRequest(BaseModel):
    note: str | None = Field(default=None, max_length=512)
    reviewed_by: str | None = Field(default=None, max_length=128)
    notify_user: bool = True


class AllowlistItem(BaseModel):
    id: UUID
    email: str
    user_id: UUID | None = None
    note: str | None = None
    created_at: datetime
    created_by: str | None = None
    revoked_at: datetime | None = None


class AllowlistListResponse(BaseModel):
    items: list[AllowlistItem]


class AllowlistAddRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    note: str | None = Field(default=None, max_length=512)
    created_by: str | None = Field(default=None, max_length=128)
    notify_user: bool = False


class AllowlistActionResponse(BaseModel):
    status: str
    email: str
    allowlisted: bool
