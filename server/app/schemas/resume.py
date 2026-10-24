"""Wire shapes for tailored resume JSON (backend SSOT)."""

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
