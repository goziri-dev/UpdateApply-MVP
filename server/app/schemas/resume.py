"""Wire shapes for tailored resume JSON (backend SSOT)."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ResumeMeta(BaseModel):
    target_role: str = ""
    company: str = ""
    version: int = 1


class ResumeBasics(BaseModel):
    name: str = ""
    email: str = ""
    location: str = ""
    links: list[str] = Field(default_factory=list)


class SkillGroup(BaseModel):
    name: str = ""
    keywords: list[str] = Field(default_factory=list)


class ExperienceItem(BaseModel):
    """Work history row. ``id`` is stable across master edits / deepen / reindex."""

    id: str = ""
    company: str = ""
    title: str = ""
    start: str = ""
    end: str = ""
    summary: str = ""
    bullets: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    school: str = ""
    degree: str = ""
    end: str = ""


class ProjectItem(BaseModel):
    """Project row. ``id`` is stable across master edits / deepen / reindex."""

    id: str = ""
    title: str = ""
    start: str = ""
    end: str = ""
    summary: str = ""
    bullets: list[str] = Field(default_factory=list)


class ResumeDocument(BaseModel):
    meta: ResumeMeta = Field(default_factory=ResumeMeta)
    basics: ResumeBasics = Field(default_factory=ResumeBasics)
    summary: str = ""
    skills: list[SkillGroup] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)


class TailorRequest(BaseModel):
    job_description: str
    target_role: str | None = None
    company: str | None = None
    # Optional override; otherwise server loads persisted profile.
    profile: dict[str, Any] | None = None


class TailorResponse(BaseModel):
    resume: ResumeDocument
    stub: bool = False
    detail: str | None = None
    # Set when the tailored resume is auto-saved as an Applications draft.
    application_id: str | None = None
    application_version: int | None = None


class ResumeTemplateInfo(BaseModel):
    id: str
    name: str
    version: str
    description: str = ""


class ResumeExportRequest(BaseModel):
    """Export PDF from the same HTML template used for preview.

    Omit ``resume`` to render the authenticated user's remade master profile
    as a ResumeDocument (post-onboarding + dashboard). Pass a tailored
    ``ResumeDocument`` when exporting a job-specific variant.
    """

    template_id: str = "classic"
    resume: ResumeDocument | None = None


class ResumeEditMode(StrEnum):
    """Agentic harness mode for ``POST /resume/edit``."""

    EDIT = "edit"
    ADVISE = "advise"
    RESEARCH_PROPOSE = "research_propose"


class ResumeEditOutcome(StrEnum):
    """User disposition of the previous proposal in this edit session."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ResumeEditRequest(BaseModel):
    """NL turn over the current ResumeDocument (propose only; no persist).

    Callers persist via PUT ``/resume/document`` (master) or PATCH
    ``/applications/{id}`` (tailored). Pass ``session_id`` to continue a
    multi-turn edit session; omit to start a new one. Optional
    ``prior_outcome`` records accept/reject of the last proposal before this
    instruction.
    """

    resume: ResumeDocument
    instruction: str = Field(min_length=1)
    mode: ResumeEditMode = ResumeEditMode.EDIT
    session_id: str | None = None
    prior_outcome: ResumeEditOutcome | None = None


class ResumeEditResponse(BaseModel):
    """Harness reply. ``resume`` is unchanged when ``applied`` is false (advise)."""

    resume: ResumeDocument
    stub: bool = False
    detail: str | None = None
    mode: ResumeEditMode = ResumeEditMode.EDIT
    session_id: str = ""
    applied: bool = True
    confidence: float | None = None


class ResumeEditProposalModel(BaseModel):
    """Structured LLM output for edit / research_propose modes."""

    resume: ResumeDocument
    detail: str = Field(
        description="Short human-readable summary of what changed (1–3 sentences)."
    )
    confidence: float | None = Field(
        default=None,
        description="0–1 confidence when research_propose; omit for plain edit.",
    )
    research_notes: str | None = Field(
        default=None,
        description="Brief notes on what research supported (research_propose).",
    )


class ResumeAdviseModel(BaseModel):
    """Structured LLM output for advise mode (no document mutation)."""

    answer: str = Field(
        description="Clear advice answering the user; do not emit a ResumeDocument."
    )


class ResumeDeepenSection(StrEnum):
    """Which list to deepen (one item at a time)."""

    EXPERIENCE = "experience"
    PROJECTS = "projects"


class ResumeDeepenMode(StrEnum):
    """Guided consultant Qs vs freeform journal dump."""

    GUIDED = "guided"
    JOURNAL = "journal"


class ResumeDeepenStartRequest(BaseModel):
    """Start optional deepen for one role/project on the current document.

    Does not flip onboarding status. Works on the client-held ResumeDocument
    (including unsaved stub rows). Assigns a stable ``id`` when missing.

    ``mode=guided`` — novel short Qs (excludes prior onboarding/deepen prompts).
    ``mode=journal`` — freeform update dump; no interview script.
    """

    resume: ResumeDocument
    section: ResumeDeepenSection
    index: int = Field(ge=0)
    mode: ResumeDeepenMode = ResumeDeepenMode.GUIDED


class ResumeDeepenTurnRequest(BaseModel):
    """Submit one deepen answer (voice transcript or typed)."""

    session_id: str
    transcript: str = ""
    force_done: bool = False


class ResumeDeepenProposeRequest(BaseModel):
    """Ask for an item-level rewrite from deepen transcripts (no persist)."""

    session_id: str


class ResumeDeepenJournalRequest(BaseModel):
    """Freeform journal dump → optional clarify or straight to enriched propose.

    Creates a journal-mode session, records the dump, and either returns a
    single clarify question (``needs_clarify``) or an enriched proposal.
    """

    resume: ResumeDocument
    section: ResumeDeepenSection
    index: int = Field(ge=0)
    text: str = Field(min_length=1, description="Freeform update / voice transcript.")
    skip_clarify: bool = False


class ResumeDeepenStateResponse(BaseModel):
    """Interview-like state for a single-item deepen session."""

    session_id: str
    stub: bool = False
    mode: str = "guided"  # guided | journal
    item_id: str
    item_kind: str  # role | project
    item_label: str = ""
    question: str | None = None
    question_index: int = 0
    question_total: int = 0
    coverage: list[str] = Field(default_factory=list)
    coverage_hits: list[str] = Field(default_factory=list)
    item_complete: bool = False
    detail: str | None = None


class ResumeDeepenTurnResponse(ResumeDeepenStateResponse):
    """Turn reply — same shape as state, plus completion flags."""


class ResumeDeepenProposeResponse(BaseModel):
    """Item-level enriched proposal merged into a full ResumeDocument (no persist)."""

    session_id: str
    stub: bool = False
    mode: str = "guided"
    item_id: str
    item_kind: str
    item: dict[str, Any]
    resume: ResumeDocument
    detail: str | None = None


class ResumeDeepenJournalResponse(BaseModel):
    """Journal dump result: either one clarify turn or a ready proposal."""

    session_id: str
    stub: bool = False
    mode: str = "journal"
    item_id: str
    item_kind: str
    item_label: str = ""
    needs_clarify: bool = False
    question: str | None = None
    item_complete: bool = False
    item: dict[str, Any] | None = None
    resume: ResumeDocument | None = None
    detail: str | None = None
