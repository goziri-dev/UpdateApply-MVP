"""Live tailor: remade profile + JD + pgvector RAG → structured resume JSON."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import Session, select

from app.core.config import Settings, get_settings
from app.core.llm_tasks import AgentTask
from app.models.profile import Profile
from app.schemas.resume import (
    ResumeDocument,
    ResumeMeta,
    TailorRequest,
    TailorResponse,
)
from app.services.agents import AgentFactory
from app.services.onboarding import profile_public
from app.services.profile_index import (
    ProfileIndexError,
    ProfileIndexService,
    get_profile_index_service,
)
from app.services.resume_document import profile_to_resume_document

logger = logging.getLogger(__name__)

TAILOR_SYSTEM_PROMPT = """\
You rewrite a candidate's remade master career profile into a tailored resume
for one specific job description.

Inputs you receive:
1. The full remade master profile (source of truth).
2. Retrieved profile chunks most relevant to the JD (RAG).
3. The pasted job description, optional target role / company.

Rules:
- Produce structured resume JSON matching the schema (meta, basics, summary,
  skills, experience, education, projects).
- Emphasize facts that match the JD; reorder and rephrase bullets for relevance.
- Honesty: do NOT invent employers, metrics, degrees, tools, or achievements that
  are not supported by the master profile or retrieved chunks.
- Prefer concrete wording from the profile; tighten for the JD without lying.
- meta.target_role / meta.company: use request hints when provided, else infer
  lightly from the JD title/company if obvious, else leave empty.
- Keep experience/project structure; drop weak bullets only when clearly
  irrelevant — do not empty the resume.
- Skills: prioritize JD-relevant keywords that exist in the profile.
"""


class TailorError(Exception):
    """Raised when live tailor fails in a user-visible way."""

    def __init__(self, message: str, *, code: str = "tailor_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class TailorService:
    """Rewrite remade profile + JD into structured resume JSON via OpenRouter."""

    def __init__(
        self,
        settings: Settings | None = None,
        index: ProfileIndexService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.agents = AgentFactory(self.settings)
        self.index = index or get_profile_index_service(self.settings)

    def tailor(
        self,
        request: TailorRequest,
        *,
        session: Session | None = None,
        user_id: UUID | None = None,
    ) -> TailorResponse:
        jd = request.job_description.strip()
        if not jd:
            raise TailorError(
                "Paste a job description before tailoring.",
                code="empty_jd",
            )

        profile_data = self._resolve_profile(
            request,
            session=session,
            user_id=user_id,
        )

        if self.agents.configured():
            return self._tailor_live(
                request,
                profile_data=profile_data,
                session=session,
                user_id=user_id,
            )

        if self.settings.allow_stub_parse:
            return self._stub_tailor(request, profile_data)

        raise TailorError(
            "Resume tailor is not configured. Set OPENROUTER_API_KEY on the server.",
            code="openrouter_unconfigured",
        )

    def _resolve_profile(
        self,
        request: TailorRequest,
        *,
        session: Session | None,
        user_id: UUID | None,
    ) -> dict[str, Any]:
        if request.profile is not None:
            return profile_public(dict(request.profile))

        if session is None or user_id is None:
            raise TailorError(
                "No profile provided and no authenticated session to load one.",
                code="missing_profile",
            )

        profile = session.exec(
            select(Profile).where(Profile.user_id == user_id)
        ).first()
        if profile is None or not (profile.data or {}):
            raise TailorError(
                "Complete onboarding and save a remade master profile before tailoring.",
                code="missing_profile",
            )
        return profile_public(dict(profile.data or {}))

    def _tailor_live(
        self,
        request: TailorRequest,
        *,
        profile_data: dict[str, Any],
        session: Session | None,
        user_id: UUID | None,
    ) -> TailorResponse:
        retrieved: list[dict[str, Any]] = []
        if session is not None and user_id is not None:
            try:
                chunks = self.index.retrieve_for_jd(
                    session,
                    user_id=user_id,
                    job_description=request.job_description,
                )
                retrieved = [
                    {
                        "chunk_type": c.chunk_type,
                        "source_item_id": c.source_item_id,
                        "text": c.text,
                    }
                    for c in chunks
                ]
            except ProfileIndexError:
                logger.exception("RAG retrieve failed; continuing with full profile")

        payload = {
            "job_description": request.job_description.strip(),
            "target_role": request.target_role or "",
            "company": request.company or "",
            "master_profile": profile_data,
            "retrieved_chunks": retrieved,
        }

        try:
            llm = self.agents.create(AgentTask.RESUME_TAILOR)
            structured = llm.with_structured_output(ResumeDocument)
            result = structured.invoke(
                [
                    SystemMessage(content=TAILOR_SYSTEM_PROMPT),
                    HumanMessage(
                        content=(
                            "Tailor this master profile to the job description. "
                            "Use retrieved chunks for emphasis; keep honesty.\n\n"
                            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
                        )
                    ),
                ]
            )
        except Exception as exc:
            logger.exception("OpenRouter resume tailor failed")
            raise TailorError(
                "Could not tailor your resume. Try again in a moment.",
                code="llm_failed",
            ) from exc

        resume = self._coerce_resume(result)
        # Prefer explicit request hints over model guesses when provided.
        if request.target_role:
            resume.meta.target_role = request.target_role
        if request.company:
            resume.meta.company = request.company

        detail = (
            f"Live tailor via {self.agents.model_for(AgentTask.RESUME_TAILOR)}; "
            f"{len(retrieved)} retrieved chunk(s)."
        )
        return TailorResponse(resume=resume, stub=False, detail=detail)

    def _stub_tailor(
        self,
        request: TailorRequest,
        profile: dict[str, Any],
    ) -> TailorResponse:
        resume = profile_to_resume_document(profile)
        resume.meta = ResumeMeta(
            target_role=request.target_role or "",
            company=request.company or "",
            version=1,
        )

        jd_preview = request.job_description.strip()[:80]
        detail = (
            "Stub tailor: returned profile-shaped JSON without LLM rewrite. "
            f"JD preview: {jd_preview!r}. "
            "Set OPENROUTER_API_KEY to enable live tailor + RAG."
        )
        return TailorResponse(resume=resume, stub=True, detail=detail)

    @staticmethod
    def _coerce_resume(result: object) -> ResumeDocument:
        if isinstance(result, ResumeDocument):
            return result
        if isinstance(result, dict):
            return ResumeDocument.model_validate(result)
        raise TailorError(
            "Tailor returned an unexpected shape. Try again.",
            code="invalid_tailor",
        )

    def _llm_ready(self) -> bool:
        return self.agents.configured()

    def build_llm_notes(self) -> dict[str, Any]:
        return {
            "model": self.agents.model_for(AgentTask.RESUME_TAILOR),
            "embedding_model": self.agents.model_for(AgentTask.EMBEDDING),
            "task": AgentTask.RESUME_TAILOR.name,
            "models": self.agents.describe_models(),
            "configured": self._llm_ready(),
        }


def get_tailor_service(settings: Settings | None = None) -> TailorService:
    return TailorService(settings=settings)
