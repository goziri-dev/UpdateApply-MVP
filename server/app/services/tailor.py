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

Inputs you receive (JSON):
1. master_resume — the remade master as ResumeDocument (source of truth).
2. retrieved_chunks — profile passages most relevant to the JD (RAG).
3. job_description, target_role, company — the pasted JD and optional hints.

Output: a ResumeDocument (meta, basics, summary, skills, experience, education,
projects). This must be a JD-specific rewrite, not a copy of master_resume.

Rules:
- Do NOT return the master unchanged. At minimum: rewrite summary for the JD,
  reorder experience/projects by relevance, and reorder/filter bullets and
  skills toward the JD. Rephrase for clarity and keyword fit when supported.
- Honesty: do NOT invent employers, metrics, degrees, tools, titles, or
  achievements that are not supported by master_resume or retrieved_chunks.
- Prefer concrete wording from the master; tighten for the JD without lying.
- Experience bullets must carry a meaningful WHY, not just what was done.
  For each bullet, make clear why the work mattered for that role/company and
  how it helped (scope, problem solved, decision rationale, or business/
  product impact). Example shape: skill/action + why it was needed here +
  what changed for the team/company. Avoid hollow lists of tools with no
  purpose (e.g. do not stop at "Used HTML/CSS/JS" — explain why those were
  the right tools for this product and what that enabled).
- Aim for 4–6 strong bullets per kept experience entry. Expand thin roles
  by splitting/rephrasing supported facts from master_resume/retrieved_chunks
  into distinct why/impact bullets. Do not invent facts just to hit the
  count; if the source truly cannot support 4, keep as many honest bullets
  as possible and prefer depth over filler. Drop a bullet only when it is
  clearly irrelevant to the JD.
- Projects: prefer the same why/impact bar; typically 3–6 bullets when the
  source supports it.
- meta.target_role / meta.company: use request hints when provided, else infer
  lightly from the JD title/company if obvious, else leave empty.
- Keep experience/project entries that still matter; drop weak bullets only when
  clearly irrelevant — do not empty the resume.
- Skills: prioritize JD-relevant keywords that already exist in the master.
- Basics / contact header: copy name, email, phone, location, citizenship,
  availability, languages, and links from master_resume unchanged. Do not
  invent or drop contact fields for the JD.
- Education: the master may mix degrees and certificates in `education`.
  Keep formal degrees when they support the candidacy. Include a certificate
  only when it is clearly relevant to the JD; omit unrelated certs/credentials.
  When including a certificate, set `kind` to `"certificate"`; for degrees use
  `kind` `"education"` (or leave empty). The rendered section title becomes
  "Education & Certificates" only if at least one certificate remains.
- Ignore any onboarding-only fields (ids, interviewed flags); they are not part
  of ResumeDocument.
"""

# Tailor = embed JD + structured rewrite; default agent timeout (60s) is tight.
_TAILOR_TIMEOUT_MS = 120_000


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
        # Master as ResumeDocument — same shape as output; no onboarding ids.
        master_resume = profile_to_resume_document(profile_data)
        retrieved = self._retrieve_chunks(
            request,
            session=session,
            user_id=user_id,
        )

        payload = {
            "job_description": request.job_description.strip(),
            "target_role": request.target_role or "",
            "company": request.company or "",
            "master_resume": master_resume.model_dump(),
            "retrieved_chunks": retrieved,
        }

        try:
            llm = self.agents.create(
                AgentTask.RESUME_TAILOR,
                timeout=_TAILOR_TIMEOUT_MS,
            )
            structured = llm.with_structured_output(ResumeDocument)
            result = structured.invoke(
                [
                    SystemMessage(content=TAILOR_SYSTEM_PROMPT),
                    HumanMessage(
                        content=(
                            "Produce a tailored ResumeDocument for this job. "
                            "Rewrite from master_resume; use retrieved_chunks for "
                            "emphasis; keep honesty — no invented facts.\n\n"
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
        # Contact/header is identity — never let the JD rewrite drop phone,
        # citizenship, availability, languages, or other master basics.
        resume.basics = master_resume.basics
        # Prefer explicit request hints over model guesses when provided.
        if request.target_role:
            resume.meta.target_role = request.target_role
        if request.company:
            resume.meta.company = request.company

        detail = (
            f"Tailored resume via {self.agents.model_for(AgentTask.RESUME_TAILOR)}; "
            f"{len(retrieved)} retrieved chunk(s)."
        )
        return TailorResponse(resume=resume, stub=False, detail=detail)

    def _retrieve_chunks(
        self,
        request: TailorRequest,
        *,
        session: Session | None,
        user_id: UUID | None,
    ) -> list[dict[str, Any]]:
        if session is None or user_id is None:
            return []
        try:
            chunks = self.index.retrieve_for_jd(
                session,
                user_id=user_id,
                job_description=request.job_description,
            )
            # Empty index → try one reindex then retrieve again.
            if not chunks:
                written = self.index.reindex_user_best_effort(session, user_id)
                if written:
                    chunks = self.index.retrieve_for_jd(
                        session,
                        user_id=user_id,
                        job_description=request.job_description,
                    )
            return [
                {
                    "chunk_type": c.chunk_type,
                    "source_item_id": c.source_item_id,
                    "text": c.text,
                }
                for c in chunks
            ]
        except ProfileIndexError:
            logger.exception("RAG retrieve failed; continuing with master resume")
            return []

    def _stub_tailor(
        self,
        request: TailorRequest,
        profile: dict[str, Any],
    ) -> TailorResponse:
        # Offline only: master mapped to ResumeDocument — not a real rewrite.
        resume = profile_to_resume_document(profile)
        resume.meta = ResumeMeta(
            target_role=request.target_role or "",
            company=request.company or "",
            version=1,
        )

        jd_preview = request.job_description.strip()[:80]
        detail = (
            "Stub tailor: returned your master resume mapped to ResumeDocument "
            "(no LLM rewrite). "
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
