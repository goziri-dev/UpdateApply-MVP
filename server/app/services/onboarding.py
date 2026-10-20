"""Onboarding helpers: profile upsert, stub PDF parse, stub interview turns.

TODO(real-parse): replace ``stub_parse_profile`` with PDF text extract + LLM
structuring (OpenRouter). Keep the same Profile JSON shape.
TODO(real-interview): replace scripted questions with an LLM interviewer that
tracks coverage + turn budget.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.models.profile import Profile
from app.models.user import User

MAX_PDF_BYTES = 10 * 1024 * 1024

# Scripted interviewer keyed by item id — mirrors prototypes/onboarding/script.js.
INTERVIEW_SCRIPTS: dict[str, dict[str, Any]] = {
    "exp-1": {
        "label": "Software Engineer · Northwind Labs",
        "kind": "role",
        "coverage": ["Scope", "Stack", "Impact", "Collaboration"],
        "questions": [
            "Walk me through what you owned day to day in this role — products, systems, or teams.",
            "You mentioned fullstack work. Besides the UI, what did you touch on the backend or data side?",
            "What outcome are you most proud of here — a metric, a launch, or a hard problem you unblocked?",
            "Anything else about this role I should capture before we move on?",
        ],
    },
    "proj-1": {
        "label": "UpdateApply (project)",
        "kind": "project",
        "coverage": ["Problem", "Approach", "Stack", "Status"],
        "questions": [
            "What problem does UpdateApply solve for you, and who is it for?",
            "How does the career profile become a tailored resume — what's the core loop?",
            "What did you build yourself versus what you're still mocking?",
            "Anything else about this project before we wrap interviews?",
        ],
    },
}


def stub_parse_profile(*, email: str | None = None) -> dict[str, Any]:
    """Return a realistic structured extract.

    Marked stub until PDF/LLM parse is wired. Shape matches resume/profile SSOT.
    """
    return {
        "basics": {
            "name": "Favour Akubuo",
            "email": email or "favour@updateapply.dev",
            "location": "Lagos, Nigeria",
            "links": [
                "linkedin.com/in/favour",
                "github.com/favour",
            ],
        },
        "summary": "",
        "skills": [
            {"name": "Languages", "keywords": ["Flutter", "Dart", "Python"]},
            {
                "name": "Backend",
                "keywords": ["FastAPI", "PostgreSQL"],
            },
            {"name": "Product", "keywords": ["Product design"]},
        ],
        "experience": [
            {
                "id": "exp-1",
                "company": "Northwind Labs",
                "title": "Software Engineer",
                "start": "2022",
                "end": "Present",
                "summary": (
                    "Built product features across API and Flutter clients; "
                    "owned resume-tailoring experiments."
                ),
                "bullets": [],
                "interviewed": False,
            }
        ],
        "education": [
            {
                "school": "Example University",
                "degree": "B.Sc. Computer Science",
                "end": "2021",
            }
        ],
        "projects": [
            {
                "id": "proj-1",
                "title": "UpdateApply",
                "start": "2025",
                "end": "Present",
                "summary": (
                    "Personal product: persist a career profile, then tailor "
                    "resumes to job descriptions."
                ),
                "bullets": [],
                "interviewed": False,
            }
        ],
    }


def interview_queue_from_profile(data: dict[str, Any]) -> list[str]:
    """All work roles + projects must be interviewed (skills excluded)."""
    queue: list[str] = []
    for item in data.get("experience") or []:
        item_id = item.get("id")
        if isinstance(item_id, str) and item_id:
            queue.append(item_id)
    for item in data.get("projects") or []:
        item_id = item.get("id")
        if isinstance(item_id, str) and item_id:
            queue.append(item_id)
    return queue


def default_onboarding_meta(
    *,
    filename: str | None = None,
    queue: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "resume_filename": filename,
        "step": "upload",
        "interview_queue": queue or [],
        "interview_index": 0,
        "question_index": 0,
        "coverage_hits": {},
    }


def get_or_create_profile(session: Session, user_id: UUID) -> Profile:
    profile = session.exec(select(Profile).where(Profile.user_id == user_id)).first()
    if profile is None:
        now = datetime.now(UTC)
        profile = Profile(
            id=uuid4(),
            user_id=user_id,
            data={},
            created_at=now,
            updated_at=now,
        )
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


def save_profile_data(
    session: Session,
    profile: Profile,
    data: dict[str, Any],
) -> Profile:
    profile.data = data
    profile.updated_at = datetime.now(UTC)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def set_user_onboarding_status(
    session: Session,
    user: User,
    status: str,
) -> User:
    user.onboarding_status = status
    user.updated_at = datetime.now(UTC)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def merge_onboarding_meta(data: dict[str, Any], **updates: Any) -> dict[str, Any]:
    out = deepcopy(data)
    meta = dict(out.get("_onboarding") or {})
    meta.update(updates)
    out["_onboarding"] = meta
    return out


def profile_public(data: dict[str, Any]) -> dict[str, Any]:
    """Strip internal ``_onboarding`` for client review payloads when desired."""
    out = deepcopy(data)
    out.pop("_onboarding", None)
    return out


def skill_labels(data: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for group in data.get("skills") or []:
        if isinstance(group, str):
            labels.append(group)
            continue
        if isinstance(group, dict):
            keywords = group.get("keywords") or []
            if keywords:
                labels.extend(str(k) for k in keywords)
            elif group.get("name"):
                labels.append(str(group["name"]))
    return labels


def apply_transcript_enrichment(
    data: dict[str, Any],
    *,
    item_id: str,
    transcript: str,
) -> dict[str, Any]:
    """Append transcript into bullets/summary for the interviewed item (stub)."""
    out = deepcopy(data)
    text = transcript.strip()
    if not text:
        return out

    for key in ("experience", "projects"):
        items = out.get(key) or []
        for item in items:
            if item.get("id") != item_id:
                continue
            bullets = list(item.get("bullets") or [])
            bullets.append(text)
            item["bullets"] = bullets
            # Prefer keeping parse summary; prepend a short note when empty.
            if not (item.get("summary") or "").strip():
                item["summary"] = text[:280]
            return out
    return out


def mark_item_interviewed(data: dict[str, Any], item_id: str) -> dict[str, Any]:
    out = deepcopy(data)
    for key in ("experience", "projects"):
        for item in out.get(key) or []:
            if item.get("id") == item_id:
                item["interviewed"] = True
    return out
