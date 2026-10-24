"""Wire shapes for Applications (tailored-resume history)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.resume import ResumeDocument


class ApplicationSummary(BaseModel):
    id: UUID
    company: str
    target_role: str
    status: str
    version: int
    job_snippet: str
    applied_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ApplicationDetail(ApplicationSummary):
    job_description: str
    resume: ResumeDocument


class ApplicationMarkAppliedRequest(BaseModel):
    """Optional override for applied_at; default is server now (UTC)."""

    applied_at: datetime | None = None


class ApplicationPatchRequest(BaseModel):
    company: str | None = None
    target_role: str | None = None
    status: str | None = Field(
        default=None,
        description="draft | applied",
    )
    applied_at: datetime | None = None


class ApplicationListResponse(BaseModel):
    items: list[ApplicationSummary]
