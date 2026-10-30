"""Structured LLM output for resume → Profile extract (TSK-12)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExtractedBasics(BaseModel):
    """Header / contact block from the resume.

    Capture every contact/header fact present on the source — not just email
    and location. Leave fields empty when absent; never invent them.
    """

    name: str = Field(default="", description="Full name as written.")
    email: str = Field(default="", description="Email address.")
    phone: str = Field(
        default="",
        description=(
            "Phone as written (e.g. +353 83 357 6161). If a garbled prefix "
            "character replaced '+', restore a leading '+' when a country "
            "code is clear."
        ),
    )
    location: str = Field(
        default="",
        description="City / region / country (e.g. Dublin, Ireland).",
    )
    citizenship: str = Field(
        default="",
        description=(
            "Citizenship or work-authorization phrase as written "
            "(e.g. Italian Citizen, EU work authorization). Empty if absent."
        ),
    )
    availability: str = Field(
        default="",
        description=(
            "Availability / notice phrase from the header when present "
            "(e.g. Available full-time). Empty if absent."
        ),
    )
    languages: list[str] = Field(
        default_factory=list,
        description=(
            "Spoken languages listed in the header/contact line "
            "(e.g. English, Italian). Prefer basics here; a Skills "
            "'Languages' group may still list them too."
        ),
    )
    links: list[str] = Field(
        default_factory=list,
        description="URLs or handles (LinkedIn, GitHub, portfolio).",
    )


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
            or (basics.phone or "").strip()
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
