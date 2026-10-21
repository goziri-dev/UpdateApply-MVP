"""Structured LLM output for resume → Profile extract (TSK-12)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExtractedBasics(BaseModel):
    name: str = ""
    email: str = ""
    location: str = ""
    links: list[str] = Field(default_factory=list)


class ExtractedSkillGroup(BaseModel):
    name: str = ""
    keywords: list[str] = Field(default_factory=list)


class ExtractedExperience(BaseModel):
    """Work history item. ``id`` may be empty; server assigns stable ids."""

    id: str = ""
    company: str = ""
    title: str = ""
    start: str = ""
    end: str = ""
    summary: str = ""
    bullets: list[str] = Field(default_factory=list)


class ExtractedEducation(BaseModel):
    school: str = ""
    degree: str = ""
    end: str = ""


class ExtractedProject(BaseModel):
    id: str = ""
    title: str = ""
    start: str = ""
    end: str = ""
    summary: str = ""
    bullets: list[str] = Field(default_factory=list)


class ExtractedProfile(BaseModel):
    """Shape mirrors persisted Profile JSONB (basics / skills / experience / …)."""

    basics: ExtractedBasics = Field(default_factory=ExtractedBasics)
    summary: str = ""
    skills: list[ExtractedSkillGroup] = Field(default_factory=list)
    experience: list[ExtractedExperience] = Field(default_factory=list)
    education: list[ExtractedEducation] = Field(default_factory=list)
    projects: list[ExtractedProject] = Field(default_factory=list)

    def to_profile_dict(self) -> dict[str, Any]:
        """Normalize to Profile payload: stable ids + ``interviewed=False``."""
        experience: list[dict[str, Any]] = []
        for i, item in enumerate(self.experience, start=1):
            raw = item.model_dump()
            item_id = (raw.get("id") or "").strip() or f"exp-{i}"
            experience.append(
                {
                    **raw,
                    "id": item_id,
                    "interviewed": False,
                }
            )

        projects: list[dict[str, Any]] = []
        for i, item in enumerate(self.projects, start=1):
            raw = item.model_dump()
            item_id = (raw.get("id") or "").strip() or f"proj-{i}"
            projects.append(
                {
                    **raw,
                    "id": item_id,
                    "interviewed": False,
                }
            )

        return {
            "basics": self.basics.model_dump(),
            "summary": self.summary,
            "skills": [s.model_dump() for s in self.skills],
            "experience": experience,
            "education": [e.model_dump() for e in self.education],
            "projects": projects,
        }

    def is_empty(self) -> bool:
        """True when extract has no usable identity or career content."""
        basics = self.basics
        has_identity = bool(
            (basics.name or "").strip()
            or (basics.email or "").strip()
            or (basics.location or "").strip()
        )
        has_career = bool(self.experience or self.projects or self.education)
        has_skills = any(
            (g.name or "").strip() or any(str(k).strip() for k in g.keywords)
            for g in self.skills
        )
        return not (
            has_identity or has_career or has_skills or (self.summary or "").strip()
        )
