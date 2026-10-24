"""Map persisted remade master profile JSON → ResumeDocument.

Post-onboarding reveal and the dashboard mini preview both use this mapping
(master profile as resume). Tailored variants come from ``TailorService`` and
are passed through export/preview as an explicit ``ResumeDocument``.
"""

from __future__ import annotations

import uuid
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

    return ensure_resume_item_ids(
        ResumeDocument(
            meta=ResumeMeta(version=1),
            basics=ResumeBasics(
                name=str(basics_raw.get("name") or ""),
                email=str(basics_raw.get("email") or ""),
                location=str(basics_raw.get("location") or ""),
                links=[
                    str(x) for x in (basics_raw.get("links") or []) if str(x).strip()
                ],
            ),
            summary=str(data.get("summary") or ""),
            skills=_skill_groups(data.get("skills")),
            experience=_experience_items(data.get("experience")),
            education=_education_items(data.get("education")),
            projects=_project_items(data.get("projects")),
        )
    )


def resume_document_to_profile_data(resume: ResumeDocument) -> dict[str, Any]:
    """Map a ResumeDocument into remade-master profile JSON fields.

    Does not include ``_onboarding`` — callers merge that from the existing
    profile row so onboarding meta is never wiped by a resume edit.
    Experience/project ``id``s are preserved (assigned when missing).
    """
    ensured = ensure_resume_item_ids(resume)
    dumped = ensured.model_dump()
    basics = dumped.get("basics") if isinstance(dumped.get("basics"), dict) else {}
    return {
        "basics": {
            "name": str(basics.get("name") or ""),
            "email": str(basics.get("email") or ""),
            "location": str(basics.get("location") or ""),
            "links": [
                str(x).strip() for x in (basics.get("links") or []) if str(x).strip()
            ],
        },
        "summary": str(dumped.get("summary") or ""),
        "skills": dumped.get("skills") or [],
        "experience": dumped.get("experience") or [],
        "education": dumped.get("education") or [],
        "projects": dumped.get("projects") or [],
    }


def merge_profile_preserving_meta(
    *,
    existing: dict[str, Any],
    resume: ResumeDocument,
) -> dict[str, Any]:
    """Build profile JSON from a ResumeDocument while keeping onboarding meta,
    deepen novelty history (``_deepen``), and ``interviewed`` flags by item id.
    """
    merged = resume_document_to_profile_data(resume)
    meta = existing.get("_onboarding")
    if isinstance(meta, dict):
        merged["_onboarding"] = meta
    deepen = existing.get("_deepen")
    if isinstance(deepen, dict):
        merged["_deepen"] = deepen

    prior_exp = {
        str(i.get("id")): i
        for i in (existing.get("experience") or [])
        if isinstance(i, dict) and i.get("id")
    }
    prior_proj = {
        str(i.get("id")): i
        for i in (existing.get("projects") or [])
        if isinstance(i, dict) and i.get("id")
    }

    experience: list[dict[str, Any]] = []
    for item in merged.get("experience") or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "")
        prior = prior_exp.get(item_id)
        row = dict(item)
        if prior is not None and "interviewed" in prior:
            row["interviewed"] = bool(prior.get("interviewed"))
        experience.append(row)
    merged["experience"] = experience

    projects: list[dict[str, Any]] = []
    for item in merged.get("projects") or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "")
        prior = prior_proj.get(item_id)
        row = dict(item)
        if prior is not None and "interviewed" in prior:
            row["interviewed"] = bool(prior.get("interviewed"))
        projects.append(row)
    merged["projects"] = projects
    return merged


def ensure_resume_item_ids(resume: ResumeDocument) -> ResumeDocument:
    """Assign stable ids to experience/project rows that lack one."""
    data = resume.model_dump()
    used: set[str] = set()

    experience: list[dict[str, Any]] = []
    for i, raw in enumerate(data.get("experience") or [], start=1):
        if not isinstance(raw, dict):
            continue
        item_id = str(raw.get("id") or "").strip()
        if not item_id or item_id in used:
            item_id = _unique_id("exp", i, used)
        used.add(item_id)
        experience.append({**raw, "id": item_id})

    projects: list[dict[str, Any]] = []
    for i, raw in enumerate(data.get("projects") or [], start=1):
        if not isinstance(raw, dict):
            continue
        item_id = str(raw.get("id") or "").strip()
        if not item_id or item_id in used:
            item_id = _unique_id("proj", i, used)
        used.add(item_id)
        projects.append({**raw, "id": item_id})

    data["experience"] = experience
    data["projects"] = projects
    return ResumeDocument.model_validate(data)


def _unique_id(prefix: str, index: int, used: set[str]) -> str:
    candidate = f"{prefix}-{index}"
    if candidate not in used:
        return candidate
    while True:
        candidate = f"{prefix}-{uuid.uuid4().hex[:10]}"
        if candidate not in used:
            return candidate


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
    for i, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        out.append(
            ExperienceItem(
                id=str(item.get("id") or "").strip() or f"exp-{i}",
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
    for i, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        out.append(
            ProjectItem(
                id=str(item.get("id") or "").strip() or f"proj-{i}",
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
