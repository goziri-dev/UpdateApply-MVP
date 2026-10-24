"""Propose hiring titles from the remade master profile (Phase 0 / TSK-26).

Suggestions are ephemeral — nothing is persisted as a confirmed target here.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.config import Settings, get_settings
from app.core.llm_tasks import AgentTask
from app.models.profile import Profile
from app.models.profile_chunk import ProfileChunk
from app.services.agents import AgentFactory
from app.services.onboarding import profile_public

logger = logging.getLogger(__name__)

# Titles that start with a skill/tool name + Engineer/Developer are dropped.
_SKILL_PREFIX = re.compile(
    r"^(?:"
    r"python|java|javascript|typescript|react|angular|vue|node(?:\.?js)?|"
    r"golang|go|rust|c\+\+|c#|kotlin|swift|ruby|php|scala|elixir|"
    r"aws|azure|gcp|sql|nosql|kubernetes|docker|terraform|"
    r"pytorch|tensorflow|hadoop|spark"
    r")[\s/\-]+(?:engineer|developer|programmer|architect)\b",
    re.IGNORECASE,
)

TITLE_SUGGESTIONS_SYSTEM = """\
You propose real hiring titles a company would post, grounded only in the
candidate's remade master career profile (and optional chunk labels).

Rules:
- Each suggestion is a hiring title (e.g. "Product Designer", "Design Engineer",
  "Staff Backend Engineer") plus one short sentence pointing at a role, project,
  or skill group on the profile.
- Prefer 3–6 suggestions. Prefer variety across seniority when the profile supports it.
- Do NOT invent employers, tools, or domains absent from the profile.
- Do NOT emit skill-shaped titles such as "Python Engineer", "React Developer",
  or "AWS Architect". Lead with the role, not the tool.
- Do NOT call ATS boards or invent job postings.
"""


class _SuggestionItem(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    reason: str = Field(min_length=8, max_length=280)


class _SuggestionPayload(BaseModel):
    suggestions: list[_SuggestionItem] = Field(default_factory=list)


class TitleSuggestionError(Exception):
    def __init__(self, message: str, *, code: str = "suggestions_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def is_skill_shaped_title(title: str) -> bool:
    """True when the title leads with a tool/language + engineer/developer."""
    cleaned = " ".join(title.strip().split())
    if not cleaned:
        return True
    return bool(_SKILL_PREFIX.match(cleaned))


def filter_skill_shaped(suggestions: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in suggestions:
        title = str(item.get("title") or "").strip()
        reason = str(item.get("reason") or "").strip()
        if not title or not reason:
            continue
        if is_skill_shaped_title(title):
            logger.info("Dropped skill-shaped title suggestion: %s", title)
            continue
        out.append({"title": title, "reason": reason})
    return out


class TitleSuggestionService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.agents = AgentFactory(self.settings)

    def suggest_for_user(self, session: Session, user_id: Any) -> list[dict[str, str]]:
        profile = session.exec(
            select(Profile).where(Profile.user_id == user_id)
        ).first()
        if profile is None or not (profile.data or {}):
            raise TitleSuggestionError(
                "Complete onboarding and save a remade master profile before "
                "getting title suggestions.",
                code="missing_profile",
            )

        public = profile_public(dict(profile.data or {}))
        # Empty remade after reset should fail closed like tailor.
        if (
            not public.get("experience")
            and not public.get("projects")
            and not public.get("summary")
            and not public.get("basics")
        ):
            raise TitleSuggestionError(
                "Complete onboarding and save a remade master profile before "
                "getting title suggestions.",
                code="missing_profile",
            )

        chunks = session.exec(
            select(ProfileChunk).where(ProfileChunk.user_id == user_id).limit(24)
        ).all()
        chunk_labels = [
            {
                "type": c.chunk_type,
                "source_item_id": c.source_item_id,
                "text": (c.text or "")[:400],
            }
            for c in chunks
        ]

        if not self.agents.configured():
            if self.settings.allow_stub_parse:
                return filter_skill_shaped(_stub_suggestions(public))
            raise TitleSuggestionError(
                "Title suggestions are not configured. Set OPENROUTER_API_KEY "
                "on the server.",
                code="openrouter_unconfigured",
            )

        try:
            llm = self.agents.create(AgentTask.TITLE_SUGGESTIONS)
            structured = llm.with_structured_output(_SuggestionPayload)
            result = structured.invoke(
                [
                    SystemMessage(content=TITLE_SUGGESTIONS_SYSTEM),
                    HumanMessage(
                        content=(
                            "Propose hiring titles for this remade master profile.\n"
                            f"master_profile={public}\n"
                            f"profile_chunks={chunk_labels}"
                        )
                    ),
                ]
            )
        except TitleSuggestionError:
            raise
        except RuntimeError as exc:
            raise TitleSuggestionError(
                str(exc) or "Title suggestions are not configured.",
                code="openrouter_unconfigured",
            ) from exc
        except (TypeError, ValueError, OSError) as exc:
            logger.exception("Title suggestions LLM failed")
            raise TitleSuggestionError(
                "Couldn’t propose titles right now. Try again in a moment.",
                code="suggestions_failed",
            ) from exc

        payload = (
            result
            if isinstance(result, _SuggestionPayload)
            else _SuggestionPayload.model_validate(result)
        )
        raw = [
            {"title": s.title.strip(), "reason": s.reason.strip()}
            for s in payload.suggestions
        ]
        return filter_skill_shaped(raw)


def _stub_suggestions(public: dict[str, Any]) -> list[dict[str, str]]:
    """Offline demo suggestions when ALLOW_STUB_PARSE and no OpenRouter."""
    titles: list[dict[str, str]] = []
    for exp in public.get("experience") or []:
        if not isinstance(exp, dict):
            continue
        role = str(exp.get("title") or exp.get("role") or "").strip()
        company = str(exp.get("company") or "").strip()
        if not role:
            continue
        reason = (
            f"Drawn from your {role} work" + (f" at {company}" if company else "") + "."
        )
        titles.append({"title": role, "reason": reason})
        if len(titles) >= 4:
            break
    if not titles:
        titles = [
            {
                "title": "Product Designer",
                "reason": "Stub suggestion from your remade master profile.",
            },
            {
                "title": "Design Engineer",
                "reason": "Stub suggestion spanning product and front-end craft.",
            },
        ]
    return titles
