"""Map persisted remade master profile JSON → ResumeDocument.

Post-onboarding reveal and the dashboard mini preview both use this mapping
(master profile as resume). Tailored variants come from ``TailorService`` and
are passed through export/preview as an explicit ``ResumeDocument``.
"""

from __future__ import annotations

from typing import Any

from app.schemas.resume import (
    EducationItem,
    ExperienceItem,
    ProjectItem,
    ResumeBasics,
    ResumeDocument,
    ResumeMeta,
    SkillGroup,
)
from app.services.onboarding import profile_public


def profile_to_resume_document(profile: dict[str, Any] | None) -> ResumeDocument:
    """Coerce public profile JSON into a typed resume for templates / PDF."""
    data = profile_public(dict(profile or {}))
    basics_raw = data.get("basics") if isinstance(data.get("basics"), dict) else {}

    return ResumeDocument(
        meta=ResumeMeta(version=1),
        basics=ResumeBasics(
            name=str(basics_raw.get("name") or ""),
            email=str(basics_raw.get("email") or ""),
            location=str(basics_raw.get("location") or ""),
            links=[str(x) for x in (basics_raw.get("links") or []) if str(x).strip()],
        ),
        summary=str(data.get("summary") or ""),
        skills=_skill_groups(data.get("skills")),
        experience=_experience_items(data.get("experience")),
        education=_education_items(data.get("education")),
        projects=_project_items(data.get("projects")),
    )


def _skill_groups(raw: object) -> list[SkillGroup]:
    out: list[SkillGroup] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.append(SkillGroup(name="", keywords=[item.strip()]))
            continue
        if not isinstance(item, dict):
            continue
        keywords = [
            str(k).strip() for k in (item.get("keywords") or []) if str(k).strip()
        ]
        name = str(item.get("name") or "").strip()
        if not name and not keywords:
            continue
        out.append(SkillGroup(name=name, keywords=keywords))
    return out


def _experience_items(raw: object) -> list[ExperienceItem]:
    out: list[ExperienceItem] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            ExperienceItem(
                company=str(item.get("company") or ""),
                title=str(item.get("title") or ""),
                start=str(item.get("start") or ""),
                end=str(item.get("end") or ""),
                summary=str(item.get("summary") or ""),
                bullets=_string_list(item.get("bullets")),
            )
        )
    return out


def _education_items(raw: object) -> list[EducationItem]:
    out: list[EducationItem] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            EducationItem(
                school=str(item.get("school") or ""),
                degree=str(item.get("degree") or ""),
                end=str(item.get("end") or ""),
            )
        )
    return out


def _project_items(raw: object) -> list[ProjectItem]:
    out: list[ProjectItem] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            ProjectItem(
                title=str(item.get("title") or ""),
                start=str(item.get("start") or ""),
                end=str(item.get("end") or ""),
                summary=str(item.get("summary") or ""),
                bullets=_string_list(item.get("bullets")),
            )
        )
    return out


def _string_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()]
