"""Thin tailor stub — OpenRouter/LangChain wiring lands behind this service."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.core.llm_tasks import AgentTask
from app.schemas.resume import (
    ExperienceItem,
    ResumeBasics,
    ResumeDocument,
    ResumeMeta,
    SkillGroup,
    TailorRequest,
    TailorResponse,
)
from app.services.agents import AgentFactory


class TailorService:
    """Rewrite profile + JD into structured resume JSON.

    MVP bootstrap returns a deterministic skeleton so the API and Flutter
    client can integrate before the LangChain chain is complete.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.agents = AgentFactory(self.settings)

    def tailor(self, request: TailorRequest) -> TailorResponse:
        if self.agents.configured():
            # Placeholder for real chain: self.agents.create(AgentTask.RESUME_TAILOR).
            # Keep stub behavior until the Implementation task lands.
            pass

        profile = request.profile or {}
        basics_raw = profile.get("basics") or {}
        skills_raw = profile.get("skills") or []
        experience_raw = profile.get("experience") or []

        resume = ResumeDocument(
            meta=ResumeMeta(
                target_role=request.target_role or "",
                company=request.company or "",
                version=1,
            ),
            basics=ResumeBasics(
                name=str(basics_raw.get("name", "")),
                email=str(basics_raw.get("email", "")),
                links=list(basics_raw.get("links") or []),
            ),
            summary=str(profile.get("summary") or ""),
            skills=[
                SkillGroup(
                    name=str(s.get("name", "")),
                    keywords=list(s.get("keywords") or []),
                )
                for s in skills_raw
                if isinstance(s, dict)
            ],
            experience=[
                ExperienceItem(
                    company=str(e.get("company", "")),
                    title=str(e.get("title", "")),
                    start=str(e.get("start", "")),
                    end=str(e.get("end", "")),
                    bullets=list(e.get("bullets") or []),
                )
                for e in experience_raw
                if isinstance(e, dict)
            ],
            education=list(profile.get("education") or []),
            projects=list(profile.get("projects") or []),
        )

        jd_preview = request.job_description.strip()[:80]
        detail = (
            "Stub tailor: returned profile-shaped JSON without LLM rewrite. "
            f"JD preview: {jd_preview!r}. "
            "Set OPENROUTER_API_KEY and implement LangChain chain to enable."
        )
        return TailorResponse(resume=resume, stub=True, detail=detail)

    def _llm_ready(self) -> bool:
        return self.agents.configured()

    def build_llm_notes(self) -> dict[str, Any]:
        return {
            "model": self.agents.model_for(AgentTask.RESUME_TAILOR),
            "task": AgentTask.RESUME_TAILOR.name,
            "models": self.agents.describe_models(),
            "configured": self._llm_ready(),
        }
