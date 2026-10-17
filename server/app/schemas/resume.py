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
    links: list[str] = Field(default_factory=list)


class SkillGroup(BaseModel):
    name: str = ""
    keywords: list[str] = Field(default_factory=list)


class ExperienceItem(BaseModel):
    company: str = ""
    title: str = ""
    start: str = ""
    end: str = ""
    bullets: list[str] = Field(default_factory=list)


class ResumeDocument(BaseModel):
    meta: ResumeMeta = Field(default_factory=ResumeMeta)
    basics: ResumeBasics = Field(default_factory=ResumeBasics)
    summary: str = ""
    skills: list[SkillGroup] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)


class TailorRequest(BaseModel):
    job_description: str
    target_role: str | None = None
    company: str | None = None
    # Optional override; otherwise server loads persisted profile.
    profile: dict[str, Any] | None = None


class TailorResponse(BaseModel):
    resume: ResumeDocument
    stub: bool = True
    detail: str | None = None
