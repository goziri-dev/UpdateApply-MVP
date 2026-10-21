"""Onboarding helpers: profile upsert, resume parse, interview turns.

Parse: PDF bytes (local storage) → markdown → ``AgentFactory`` RESUME_EXTRACT.
Interview: LLM scripts via ``AgentTask.INTERVIEW_QUESTIONS`` (stub only when
``ALLOW_STUB_PARSE`` and OpenRouter is off).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.core.config import Settings, get_settings
from app.models.profile import Profile
from app.models.user import User
from app.services.extract import ExtractError, ResumeExtractService
from app.services.interview_questions import (
    INTERVIEW_SCRIPT_VERSION,
    InterviewError,
    InterviewQuestionService,
)
from app.services.resume_storage import ResumeStorage

MAX_PDF_BYTES = 10 * 1024 * 1024

# Offline click-through only (ALLOW_STUB_PARSE + no OpenRouter). Mirrors
# prototypes/onboarding/script.js for the demo stub profile ids.
STUB_INTERVIEW_SCRIPTS: dict[str, dict[str, Any]] = {
    "exp-1": {
        "label": "Software Engineer · Northwind Labs",
        "kind": "role",
        "coverage": ["Day-to-day", "Tools", "Outcomes", "How you worked"],
        "questions": [
            "What did a typical stretch of work look like here — products, systems, or people you spent time with? No pressure if memory is fuzzy.",
            "You mentioned fullstack work. Besides the UI, what else did you touch — backend, data, or something shared with the team?",
            "Looking back, what would you want a friend to understand about what you actually did here — a launch, a hard problem, or something quieter?",
            "Anything else you'd like to add about this role before we move on? No rush if not.",
        ],
    },
    "proj-1": {
        "label": "UpdateApply (project)",
        "kind": "project",
        "coverage": [
            "Why it exists",
            "How you approached it",
            "Tools",
            "Where it stands",
        ],
        "questions": [
            "What was UpdateApply trying to make easier for you, and who did you have in mind?",
            "In your own words, how does the career profile turn into a tailored resume — what's the loop that matters?",
            "What felt like yours to build versus still rough or mocked — and is it okay if some of that is still fuzzy?",
            "Anything else you'd like to add about this project before we move on? No rush if not.",
        ],
    },
}


def stub_parse_profile(*, email: str | None = None) -> dict[str, Any]:
    """Demo structured extract for offline click-through only.

    Gated by ``Settings.allow_stub_parse``. Normal parse never calls this.
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


def parse_resume_to_profile(
    *,
    user_id: UUID,
    email: str | None = None,
    filename: str = "resume.pdf",
    settings: Settings | None = None,
) -> tuple[dict[str, Any], bool]:
    """Load stored PDF → LLM extract (or gated stub).

    Returns:
        ``(profile_dict, stub)`` where ``stub`` is True only for explicit stub path.

    Raises:
        ExtractError: missing PDF, empty/failed extract, or OpenRouter unavailable
            when stub is not allowed.
    """
    cfg = settings or get_settings()
    storage = ResumeStorage(cfg)
    raw = storage.load(user_id)

    if raw is None:
        if cfg.allow_stub_parse:
            return stub_parse_profile(email=email), True
        raise ExtractError(
            "Upload a PDF resume before parsing.",
            code="missing_pdf",
        )

    if cfg.openrouter_configured:
        extracted = ResumeExtractService(cfg).extract_from_pdf_bytes(
            raw,
            filename=filename,
            email_hint=email,
        )
        return extracted, False

    if cfg.allow_stub_parse:
        return stub_parse_profile(email=email), True

    raise ExtractError(
        "Resume extract is not configured. Set OPENROUTER_API_KEY on the server.",
        code="openrouter_unconfigured",
    )


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


def find_profile_item(
    data: dict[str, Any], item_id: str
) -> tuple[dict[str, Any], Literal["role", "project"]] | None:
    """Locate an experience/project by id. Skills are never interview targets."""
    for item in data.get("experience") or []:
        if isinstance(item, dict) and item.get("id") == item_id:
            return item, "role"
    for item in data.get("projects") or []:
        if isinstance(item, dict) and item.get("id") == item_id:
            return item, "project"
    return None


def profile_item_label(
    data: dict[str, Any], item_id: str
) -> tuple[str, Literal["role", "project"]]:
    """Human label for queue chips without requiring an LLM script."""
    found = find_profile_item(data, item_id)
    if found is None:
        return item_id, "role"
    item, kind = found
    if kind == "project":
        title = str(item.get("title") or "Project").strip() or "Project"
        return f"{title} (project)", "project"
    title = str(item.get("title") or "Role").strip() or "Role"
    company = str(item.get("company") or "").strip()
    label = f"{title} · {company}" if company else title
    return label, "role"


def _stub_script_for_item(data: dict[str, Any], item_id: str) -> dict[str, Any]:
    """Gated offline scripts for demo profile ids; generic fallback otherwise."""
    if item_id in STUB_INTERVIEW_SCRIPTS:
        return deepcopy(STUB_INTERVIEW_SCRIPTS[item_id])
    label, kind = profile_item_label(data, item_id)
    if kind == "project":
        return {
            "label": label,
            "kind": "project",
            "coverage": [
                "Why it exists",
                "How you approached it",
                "Tools",
                "Where it stands",
            ],
            "questions": [
                f"What was {label} trying to make easier, and who did you have in mind?",
                "How did you approach it, and what felt like yours versus shared or still rough?",
                "Where does it stand now, and what would you explore next if you had time?",
                "Anything else you'd like to add about this project before we move on? No rush if not.",
            ],
        }
    return {
        "label": label,
        "kind": "role",
        "coverage": ["Day-to-day", "Tools", "Outcomes", "How you worked"],
        "questions": [
            "What did day-to-day work look like in this role? No pressure if memory is fuzzy.",
            "What tools or systems did you spend the most time with?",
            "What would you want a friend to understand about what you actually did here?",
            "Anything else you'd like to add about this role before we move on? No rush if not.",
        ],
    }


def cached_interview_script(
    data: dict[str, Any], item_id: str
) -> dict[str, Any] | None:
    meta = data.get("_onboarding") if isinstance(data.get("_onboarding"), dict) else {}
    scripts = meta.get("item_scripts") if isinstance(meta, dict) else None
    if not isinstance(scripts, dict):
        return None
    raw = scripts.get(item_id)
    if not isinstance(raw, dict):
        return None
    if raw.get("script_version") != INTERVIEW_SCRIPT_VERSION:
        return None
    questions = raw.get("questions")
    if not isinstance(questions, list) or not questions:
        return None
    return {
        "label": str(raw.get("label") or item_id),
        "kind": raw.get("kind") if raw.get("kind") in ("role", "project") else "role",
        "coverage": [str(c) for c in list(raw.get("coverage") or [])],
        "questions": [str(q) for q in questions],
    }


def store_interview_script(
    data: dict[str, Any], item_id: str, script: dict[str, Any]
) -> dict[str, Any]:
    out = deepcopy(data)
    meta = dict(out.get("_onboarding") or {})
    scripts = dict(meta.get("item_scripts") or {})
    scripts[item_id] = {
        "label": script["label"],
        "kind": script["kind"],
        "coverage": list(script.get("coverage") or []),
        "questions": list(script.get("questions") or []),
        "script_version": INTERVIEW_SCRIPT_VERSION,
    }
    meta["item_scripts"] = scripts
    out["_onboarding"] = meta
    return out


def ensure_interview_script(
    data: dict[str, Any],
    item_id: str,
    *,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Return ``(script, data, stub)``, generating + caching when missing.

    Live path (OpenRouter configured): LLM via ``InterviewQuestionService``.
    Stub path: only when ``allow_stub_parse`` and OpenRouter is off.
    """
    cached = cached_interview_script(data, item_id)
    if cached is not None:
        cfg = settings or get_settings()
        return cached, data, not cfg.openrouter_configured

    cfg = settings or get_settings()
    found = find_profile_item(data, item_id)
    if found is None:
        raise InterviewError(
            f"Unknown interview item {item_id!r}. Re-parse your resume and try again.",
            code="unknown_item",
        )
    item, kind = found
    basics = data.get("basics") if isinstance(data.get("basics"), dict) else {}

    if cfg.openrouter_configured:
        script = InterviewQuestionService(cfg).generate_for_item(
            item=item,
            kind=kind,
            basics=basics,
        )
        updated = store_interview_script(data, item_id, script)
        return script, updated, False

    if cfg.allow_stub_parse:
        script = _stub_script_for_item(data, item_id)
        updated = store_interview_script(data, item_id, script)
        return script, updated, True

    raise InterviewError(
        "Interview questions are not configured. Set OPENROUTER_API_KEY on the server.",
        code="openrouter_unconfigured",
    )


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
