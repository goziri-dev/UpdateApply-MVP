"""Onboarding API contracts (upload → parse → interview → review → complete)."""

from typing import Any, Literal

from pydantic import BaseModel, Field

OnboardingStatus = Literal["not_started", "in_progress", "complete"]
InterviewItemKind = Literal["role", "project"]


class OnboardingStatusResponse(BaseModel):
    status: OnboardingStatus
    step: str | None = None
    has_profile: bool = False
    resume_filename: str | None = None


class OnboardingUploadResponse(BaseModel):
    status: OnboardingStatus
    filename: str
    size_bytes: int
    detail: str = "PDF accepted. Call parse to extract a structured profile."


class OnboardingParseResponse(BaseModel):
    """Structured extract after parse. ``stub=True`` until real LLM/PDF extract ships."""

    status: OnboardingStatus
    stub: bool = True
    detail: str | None = None
    profile: dict[str, Any]
    interview_queue: list[str] = Field(default_factory=list)


class InterviewTurnRequest(BaseModel):
    item_id: str
    transcript: str = ""
    force_done: bool = False


class InterviewTurnResponse(BaseModel):
    """Next question or advance signal. LLM interviewer is stubbed for MVP."""

    stub: bool = True
    item_id: str
    item_kind: InterviewItemKind
    item_label: str
    question: str | None = None
    question_index: int = 0
    question_total: int = 0
    coverage: list[str] = Field(default_factory=list)
    coverage_hits: list[str] = Field(default_factory=list)
    item_complete: bool = False
    interview_complete: bool = False
    next_item_id: str | None = None
    enriched_summary: str | None = None
    detail: str | None = None


class InterviewStateResponse(BaseModel):
    """Current interview cursor for resuming the Flutter flow."""

    stub: bool = True
    interview_complete: bool = False
    item_id: str | None = None
    item_kind: InterviewItemKind | None = None
    item_label: str | None = None
    question: str | None = None
    question_index: int = 0
    question_total: int = 0
    coverage: list[str] = Field(default_factory=list)
    coverage_hits: list[str] = Field(default_factory=list)
    queue: list[dict[str, Any]] = Field(default_factory=list)


class OnboardingProfileUpdate(BaseModel):
    """Review-screen edits. Client sends the full editable profile slice."""

    data: dict[str, Any]


class OnboardingCompleteResponse(BaseModel):
    status: OnboardingStatus
    detail: str = "Onboarding complete. Hard gate cleared."
