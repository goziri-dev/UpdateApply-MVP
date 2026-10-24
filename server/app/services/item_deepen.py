"""Optional post-onboarding item deepen: guided novel Qs or journal dump → rewrite."""

from __future__ import annotations

import json
import logging
import re
from copy import deepcopy
from typing import Any, Literal
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.config import Settings, get_settings
from app.core.llm_tasks import AgentTask
from app.schemas.resume import (
    ExperienceItem,
    ProjectItem,
    ResumeDeepenJournalRequest,
    ResumeDeepenJournalResponse,
    ResumeDeepenMode,
    ResumeDeepenProposeRequest,
    ResumeDeepenProposeResponse,
    ResumeDeepenSection,
    ResumeDeepenStartRequest,
    ResumeDeepenStateResponse,
    ResumeDeepenTurnRequest,
    ResumeDeepenTurnResponse,
    ResumeDocument,
)
from app.services.agents import AgentFactory
from app.services.deepen_history import collect_prior_for_item, record_deepen_session
from app.services.deepen_session import (
    DeepenSession,
    get_deepen_session_store,
    new_session_id,
)
from app.services.interview_questions import InterviewError, InterviewQuestionService
from app.services.onboarding import get_or_create_profile, save_profile_data
from app.services.resume_document import ensure_resume_item_ids

logger = logging.getLogger(__name__)

ITEM_DEEPEN_SYSTEM_PROMPT = """\
You enrich ONE resume item (a work role OR a project) using clarifying
conversation transcripts OR a freeform journal dump. Return only that item —
not a full resume remake.

Inputs:
1. kind — role or project
2. item — current fields (id, title/company, dates, summary, bullets)
3. conversation — Q&A turns and/or a journal dump about this item only
4. coverage themes that were touched (may be empty for journal)
5. mode — guided | journal

Rules:
- Weave answers into a stronger summary and bullets (not a transcript dump).
- Preserve id, employer/title/school identity, and dates unless the conversation
  clearly corrects them.
- Prefer concrete verbs, scope, tools, and outcomes when the conversation
  supplies them; keep existing wording when conversation is thin.
- Honesty: do NOT invent metrics, employers, products, tools, or titles that are
  not supported by the current item or the conversation.
- Keep bullet count reasonable (typically 3–6). Do not paste every spoken sentence.
"""

JOURNAL_CLARIFY_SYSTEM = """\
You review a freeform career update dump for ONE resume item.
If something critical is ambiguous for writing honest resume bullets
(e.g. unclear employer/role, contradictory dates, or a claim that cannot be
woven without guessing), return needs_clarify=true and ONE short consultant-tone
clarify question. Otherwise needs_clarify=false and clarify_question empty.
Do not ask generic day-to-day questions. Prefer no clarify when the dump is usable.
"""


class ItemDeepenError(Exception):
    """User-visible deepen failure."""

    def __init__(self, message: str, *, code: str = "deepen_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class _RoleEnrichment(BaseModel):
    item: ExperienceItem
    detail: str = Field(
        description="1–2 sentences summarizing what was enriched from the conversation."
    )


class _ProjectEnrichment(BaseModel):
    item: ProjectItem
    detail: str = Field(
        description="1–2 sentences summarizing what was enriched from the conversation."
    )


class _JournalClarify(BaseModel):
    needs_clarify: bool = False
    clarify_question: str = Field(
        default="",
        description="One short question if needs_clarify; else empty.",
    )


class ItemDeepenService:
    """Start / turn / propose / journal for one-item deepen (no onboarding gate)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.agents = AgentFactory(self.settings)
        self.sessions = get_deepen_session_store()
        self.questions = InterviewQuestionService(self.settings)

    def start(
        self,
        *,
        user_id: Any,
        body: ResumeDeepenStartRequest,
        db: Session | None = None,
    ) -> ResumeDeepenStateResponse:
        resume = ensure_resume_item_ids(body.resume)
        section = body.section.value
        items = (
            resume.experience
            if body.section is ResumeDeepenSection.EXPERIENCE
            else resume.projects
        )
        if body.index >= len(items):
            raise ItemDeepenError(
                f"No {section} entry at index {body.index}.",
                code="bad_index",
            )

        item = items[body.index]
        item_id = (item.id or "").strip()
        if not item_id:
            raise ItemDeepenError(
                "Item is missing an id after ensure — cannot deepen.",
                code="missing_id",
            )

        kind: Literal["role", "project"] = (
            "role" if body.section is ResumeDeepenSection.EXPERIENCE else "project"
        )
        item_dict = item.model_dump()
        basics = resume.basics.model_dump()
        mode: Literal["guided", "journal"] = (
            "journal" if body.mode is ResumeDeepenMode.JOURNAL else "guided"
        )

        if mode == "journal":
            label = self._default_label(kind, item_dict)
            script = {
                "label": label,
                "kind": kind,
                "coverage": ["Journal update"],
                "questions": [],
            }
            stub = False
        else:
            prior = self._load_prior(db=db, user_id=user_id, item_id=item_id)
            try:
                script, stub = self._script_for_deepen(
                    item=item_dict,
                    kind=kind,
                    basics=basics,
                    prior_questions=list(prior.get("asked_questions") or []),
                    prior_themes=list(prior.get("themes") or []),
                )
            except InterviewError as exc:
                raise ItemDeepenError(exc.message, code=exc.code) from exc

        session = DeepenSession(
            session_id=new_session_id(),
            user_id=user_id,
            section=section,  # type: ignore[arg-type]
            index=body.index,
            item_id=item_id,
            kind=kind,
            resume=resume.model_dump(),
            script=script,
            mode=mode,
            stub=stub if mode == "guided" else False,
        )
        self.sessions.create(session)
        return self._state(session)

    def journal(
        self,
        *,
        user_id: Any,
        body: ResumeDeepenJournalRequest,
        db: Session | None = None,
    ) -> ResumeDeepenJournalResponse:
        """One-shot journal dump: optional single clarify, else propose."""
        start_body = ResumeDeepenStartRequest(
            resume=body.resume,
            section=body.section,
            index=body.index,
            mode=ResumeDeepenMode.JOURNAL,
        )
        state = self.start(user_id=user_id, body=start_body, db=db)
        session = self._require(user_id, state.session_id)

        text = body.text.strip()
        if not text:
            raise ItemDeepenError(
                "Add a short update (record or type) before continuing.",
                code="empty_transcript",
            )

        session.transcripts.append(
            {
                "question": None,
                "question_index": 0,
                "answer": text,
                "source": "journal",
            }
        )
        if "Journal update" not in session.coverage_hits:
            session.coverage_hits.append("Journal update")

        clarify: str | None = None
        if not body.skip_clarify:
            clarify = self._maybe_journal_clarify(
                kind=session.kind,
                item=self._current_item(
                    session, ResumeDocument.model_validate(session.resume)
                ),
                dump=text,
            )

        if clarify:
            session.clarify_pending = True
            session.script = {
                **session.script,
                "questions": [clarify],
                "coverage": list(session.script.get("coverage") or ["Journal update"])
                + (
                    ["Clarify"]
                    if "Clarify" not in (session.script.get("coverage") or [])
                    else []
                ),
            }
            session.question_index = 0
            session.item_complete = False
            self.sessions.touch(session)
            return ResumeDeepenJournalResponse(
                session_id=session.session_id,
                stub=session.stub,
                mode="journal",
                item_id=session.item_id,
                item_kind=session.kind,
                item_label=str(session.script.get("label") or session.item_id),
                needs_clarify=True,
                question=clarify,
                item_complete=False,
                detail="One quick clarify — then we can propose an enriched item.",
            )

        session.item_complete = True
        session.clarify_pending = False
        self.sessions.touch(session)
        proposed = self.propose(
            user_id=user_id,
            body=ResumeDeepenProposeRequest(session_id=session.session_id),
            db=db,
        )
        return ResumeDeepenJournalResponse(
            session_id=proposed.session_id,
            stub=proposed.stub,
            mode="journal",
            item_id=proposed.item_id,
            item_kind=proposed.item_kind,
            item_label=str(session.script.get("label") or session.item_id),
            needs_clarify=False,
            question=None,
            item_complete=True,
            item=proposed.item,
            resume=proposed.resume,
            detail=proposed.detail,
        )

    def state(self, *, user_id: Any, session_id: str) -> ResumeDeepenStateResponse:
        session = self._require(user_id, session_id)
        return self._state(session)

    def turn(
        self,
        *,
        user_id: Any,
        body: ResumeDeepenTurnRequest,
        db: Session | None = None,
    ) -> ResumeDeepenTurnResponse:
        session = self._require(user_id, body.session_id)
        if session.item_complete:
            return ResumeDeepenTurnResponse(
                **self._state(session).model_dump(),
                detail="This item’s deepen chat is already finished.",
            )

        transcript = body.transcript.strip()
        if not transcript and not body.force_done:
            raise ItemDeepenError(
                "Add a short answer (record or type) before continuing.",
                code="empty_transcript",
            )

        # Journal mode: dump (or clarify answer) then complete.
        if session.mode == "journal":
            questions: list[str] = [
                str(q) for q in list(session.script.get("questions") or [])
            ]
            current_question = (
                questions[0] if session.clarify_pending and questions else None
            )
            if transcript:
                session.transcripts.append(
                    {
                        "question": current_question,
                        "question_index": 0,
                        "answer": transcript,
                        "source": "clarify" if session.clarify_pending else "journal",
                    }
                )
                if "Journal update" not in session.coverage_hits:
                    session.coverage_hits.append("Journal update")
                if session.clarify_pending and "Clarify" not in session.coverage_hits:
                    session.coverage_hits.append("Clarify")
            session.clarify_pending = False
            session.item_complete = True
            self.sessions.touch(session)
            _ = db  # history recorded on propose
            return ResumeDeepenTurnResponse(
                **self._state(session).model_dump(),
                detail="Done with this update — propose an enriched version when ready.",
            )

        questions = [str(q) for q in list(session.script.get("questions") or [])]
        coverage: list[str] = [
            str(c) for c in list(session.script.get("coverage") or [])
        ]
        q_index = session.question_index

        current_question = (
            questions[q_index] if questions and q_index < len(questions) else None
        )
        if transcript:
            session.transcripts.append(
                {
                    "question": current_question,
                    "question_index": q_index,
                    "answer": transcript,
                }
            )
            if coverage:
                hit = coverage[min(q_index, len(coverage) - 1)]
                if hit not in session.coverage_hits:
                    session.coverage_hits.append(hit)
            if q_index >= 1 and len(coverage) > 1:
                second = coverage[1]
                if second not in session.coverage_hits:
                    session.coverage_hits.append(second)

        last_q = q_index >= max(len(questions) - 1, 0)
        finish = body.force_done or last_q or ("that's all" in transcript.lower())

        if finish:
            session.item_complete = True
            session.question_index = q_index
            self.sessions.touch(session)
            return ResumeDeepenTurnResponse(
                **self._state(session).model_dump(),
                detail="Done with this item — propose an enriched version when ready.",
            )

        session.question_index = q_index + 1
        self.sessions.touch(session)
        return ResumeDeepenTurnResponse(**self._state(session).model_dump())

    def propose(
        self,
        *,
        user_id: Any,
        body: ResumeDeepenProposeRequest,
        db: Session | None = None,
    ) -> ResumeDeepenProposeResponse:
        session = self._require(user_id, body.session_id)
        if not session.transcripts and not session.item_complete:
            raise ItemDeepenError(
                "Add at least one answer before proposing an enriched item.",
                code="empty_interview",
            )

        resume = ResumeDocument.model_validate(session.resume)
        current = self._current_item(session, resume)

        if not self.agents.configured():
            if self.settings.allow_stub_parse:
                enriched = self._stub_enrich(current, session.transcripts)
                detail = (
                    "STUB DEEPEN: wove answers into summary/bullets (ALLOW_STUB_PARSE)."
                )
                merged = self._merge_item(resume, session, enriched)
                session.proposed_item = enriched
                self._persist_history(db=db, user_id=user_id, session=session)
                self.sessions.touch(session)
                return ResumeDeepenProposeResponse(
                    session_id=session.session_id,
                    stub=True,
                    mode=session.mode,
                    item_id=session.item_id,
                    item_kind=session.kind,
                    item=enriched,
                    resume=merged,
                    detail=detail,
                )
            raise ItemDeepenError(
                "Item deepen is not configured. Set OPENROUTER_API_KEY on the server.",
                code="openrouter_unconfigured",
            )

        try:
            enriched, detail = self._rewrite_item(
                kind=session.kind,
                item=current,
                transcripts=session.transcripts,
                coverage_hits=session.coverage_hits,
                mode=session.mode,
            )
        except ItemDeepenError:
            raise
        except Exception as exc:
            logger.exception("item deepen rewrite failed")
            raise ItemDeepenError(
                "Could not enrich this item. Try again in a moment.",
                code="llm_failed",
            ) from exc

        enriched["id"] = session.item_id
        merged = self._merge_item(resume, session, enriched)
        session.proposed_item = enriched
        session.resume = merged.model_dump()
        self._persist_history(db=db, user_id=user_id, session=session)
        self.sessions.touch(session)
        return ResumeDeepenProposeResponse(
            session_id=session.session_id,
            stub=False,
            mode=session.mode,
            item_id=session.item_id,
            item_kind=session.kind,
            item=enriched,
            resume=merged,
            detail=detail,
        )

    def clear(self, *, user_id: Any, session_id: str) -> bool:
        return self.sessions.delete(user_id=user_id, session_id=session_id)

    def _require(self, user_id: Any, session_id: str) -> DeepenSession:
        session = self.sessions.get(user_id=user_id, session_id=session_id)
        if session is None:
            raise ItemDeepenError(
                "Deepen session not found or expired. Start again from the editor.",
                code="unknown_session",
            )
        return session

    def _state(self, session: DeepenSession) -> ResumeDeepenStateResponse:
        questions = [str(q) for q in list(session.script.get("questions") or [])]
        coverage = [str(c) for c in list(session.script.get("coverage") or [])]
        q_index = min(session.question_index, max(len(questions) - 1, 0))
        question = None
        if not session.item_complete:
            if session.mode == "journal" and not session.clarify_pending:
                question = None
            elif questions:
                question = questions[q_index]
        return ResumeDeepenStateResponse(
            session_id=session.session_id,
            stub=session.stub,
            mode=session.mode,
            item_id=session.item_id,
            item_kind=session.kind,
            item_label=str(session.script.get("label") or session.item_id),
            question=question,
            question_index=q_index if questions else 0,
            question_total=len(questions)
            if session.mode == "guided"
            else (1 if session.clarify_pending else 0),
            coverage=coverage,
            coverage_hits=list(session.coverage_hits),
            item_complete=session.item_complete,
        )

    def _load_prior(
        self, *, db: Session | None, user_id: Any, item_id: str
    ) -> dict[str, Any]:
        if db is None:
            return {"asked_questions": [], "themes": []}
        try:
            uid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
            profile = get_or_create_profile(db, uid)
            return collect_prior_for_item(dict(profile.data or {}), item_id)
        except Exception:
            logger.exception("deepen prior load failed; continuing without history")
            return {"asked_questions": [], "themes": []}

    def _persist_history(
        self, *, db: Session | None, user_id: Any, session: DeepenSession
    ) -> None:
        if session.history_recorded or db is None:
            return
        questions = [
            str(t.get("question") or "").strip()
            for t in session.transcripts
            if str(t.get("question") or "").strip()
        ]
        # Also record script questions that were generated even if unanswered.
        for q in session.script.get("questions") or []:
            text = str(q or "").strip()
            if text and text not in questions:
                questions.append(text)
        themes = list(session.coverage_hits) or list(
            session.script.get("coverage") or []
        )
        try:
            uid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
            profile = get_or_create_profile(db, uid)
            data = record_deepen_session(
                dict(profile.data or {}),
                item_id=session.item_id,
                mode=session.mode,
                questions=questions,
                themes=themes,
                transcripts=session.transcripts,
            )
            save_profile_data(db, profile, data)
            session.history_recorded = True
        except Exception:
            logger.exception("deepen history persist failed")

    def _script_for_deepen(
        self,
        *,
        item: dict[str, Any],
        kind: Literal["role", "project"],
        basics: dict[str, Any],
        prior_questions: list[str],
        prior_themes: list[str],
    ) -> tuple[dict[str, Any], bool]:
        if self.agents.configured():
            script = self.questions.generate_deepen_for_item(
                item=item,
                kind=kind,
                basics=basics,
                prior_questions=prior_questions,
                prior_themes=prior_themes,
            )
            return script, False
        if self.settings.allow_stub_parse:
            return self._stub_deepen_script(
                item=item,
                kind=kind,
                prior_questions=prior_questions,
            ), True
        raise InterviewError(
            "Interview questions are not configured. Set OPENROUTER_API_KEY on the server.",
            code="openrouter_unconfigured",
        )

    @staticmethod
    def _default_label(kind: Literal["role", "project"], item: dict[str, Any]) -> str:
        if kind == "project":
            title = str(item.get("title") or "Project").strip() or "Project"
            return f"{title} (project)"
        title = str(item.get("title") or "Role").strip() or "Role"
        company = str(item.get("company") or "").strip()
        return f"{title} · {company}" if company else title

    def _stub_deepen_script(
        self,
        *,
        item: dict[str, Any],
        kind: Literal["role", "project"],
        prior_questions: list[str],
    ) -> dict[str, Any]:
        label = self._default_label(kind, item)
        # Novel stub prompts — deliberately not Day-to-day / typical week.
        if kind == "project":
            candidates = [
                (
                    "What changed",
                    "What’s one concrete thing that changed because of this project?",
                ),
                (
                    "Your slice",
                    "Which part of this felt most like yours — and what did you hand off?",
                ),
                (
                    "Constraints",
                    "What constraint (time, tools, people) shaped how you built it?",
                ),
            ]
        else:
            candidates = [
                (
                    "Scope you owned",
                    "What slice of work were you trusted to own end-to-end here?",
                ),
                (
                    "Tools in the loop",
                    "Which tools or systems were you actually in every week?",
                ),
                (
                    "What shifted",
                    "What’s one thing that got easier or clearer because of your work?",
                ),
            ]
        prior_low = {p.casefold() for p in prior_questions if p.strip()}
        picked: list[tuple[str, str]] = []
        for theme, q in candidates:
            if q.casefold() in prior_low:
                continue
            picked.append((theme, q))
            if len(picked) >= 3:
                break
        if not picked:
            picked = candidates[:2]
        wrap = (
            "Anything else you’d like to add about this before we wrap? No rush if not."
        )
        questions = [q for _, q in picked] + [wrap]
        coverage = [t for t, _ in picked]
        return {
            "label": label,
            "kind": kind,
            "coverage": coverage,
            "questions": questions,
        }

    def _maybe_journal_clarify(
        self,
        *,
        kind: Literal["role", "project"],
        item: dict[str, Any],
        dump: str,
    ) -> str | None:
        # Heuristic: very short dumps often need a nudge; skip LLM if stub-only.
        if len(dump.split()) < 8:
            return (
                "Could you add one concrete detail — what you did, with what, "
                "or what changed?"
            )

        if not self.agents.configured():
            # Ambiguity heuristic without LLM: pronoun-heavy / no noun overlap.
            if (
                re.search(r"\b(they|someone|somewhere)\b", dump, re.IGNORECASE)
                and len(dump.split()) < 40
            ):
                return (
                    "Who or what does that refer to in this role/project — "
                    "so we don’t guess on the resume?"
                )
            return None

        try:
            llm = self.agents.create(AgentTask.PROFILE_REVIEW)
            structured = llm.with_structured_output(_JournalClarify)
            result = structured.invoke(
                [
                    SystemMessage(content=JOURNAL_CLARIFY_SYSTEM),
                    HumanMessage(
                        content=json.dumps(
                            {"kind": kind, "item": item, "dump": dump},
                            ensure_ascii=False,
                            indent=2,
                        )
                    ),
                ]
            )
            model = (
                result
                if isinstance(result, _JournalClarify)
                else _JournalClarify.model_validate(result)
            )
            if model.needs_clarify and model.clarify_question.strip():
                return model.clarify_question.strip()
        except Exception:
            logger.exception("journal clarify check failed; skipping clarify")
        return None

    @staticmethod
    def _current_item(session: DeepenSession, resume: ResumeDocument) -> dict[str, Any]:
        if session.section == "experience":
            return resume.experience[session.index].model_dump()
        return resume.projects[session.index].model_dump()

    @staticmethod
    def _merge_item(
        resume: ResumeDocument,
        session: DeepenSession,
        enriched: dict[str, Any],
    ) -> ResumeDocument:
        data = resume.model_dump()
        key = "experience" if session.section == "experience" else "projects"
        items = list(data.get(key) or [])
        if session.index < len(items):
            items[session.index] = {
                **items[session.index],
                **enriched,
                "id": session.item_id,
            }
            data[key] = items
        return ResumeDocument.model_validate(data)

    def _rewrite_item(
        self,
        *,
        kind: Literal["role", "project"],
        item: dict[str, Any],
        transcripts: list[dict[str, Any]],
        coverage_hits: list[str],
        mode: Literal["guided", "journal"],
    ) -> tuple[dict[str, Any], str]:
        payload = {
            "kind": kind,
            "mode": mode,
            "item": item,
            "conversation": transcripts,
            "coverage_hits": coverage_hits,
        }
        llm = self.agents.create(AgentTask.PROFILE_REVIEW)
        if kind == "role":
            structured = llm.with_structured_output(_RoleEnrichment)
        else:
            structured = llm.with_structured_output(_ProjectEnrichment)
        result = structured.invoke(
            [
                SystemMessage(content=ITEM_DEEPEN_SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        "Enrich this single resume item from the conversation.\n"
                        "Do not invent unverifiable facts.\n\n"
                        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
                    )
                ),
            ]
        )
        if kind == "role":
            model = (
                result
                if isinstance(result, _RoleEnrichment)
                else _RoleEnrichment.model_validate(result)
            )
        else:
            model = (
                result
                if isinstance(result, _ProjectEnrichment)
                else _ProjectEnrichment.model_validate(result)
            )
        out = model.item.model_dump()
        return out, (model.detail or "").strip() or "Enriched from your answers."

    @staticmethod
    def _stub_enrich(
        item: dict[str, Any], transcripts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        out = deepcopy(item)
        answers = [
            str(t.get("answer") or "").strip()
            for t in transcripts
            if str(t.get("answer") or "").strip()
        ]
        if not answers:
            return out
        joined = " ".join(answers)
        base = str(out.get("summary") or "").strip()
        clause = answers[0][:160].rstrip()
        if not base:
            out["summary"] = joined[:320].rstrip()
        elif clause and clause.lower() not in base.lower():
            out["summary"] = f"{base} Clarified: {clause}"
        bullets = [str(b) for b in (out.get("bullets") or []) if str(b).strip()]
        for ans in answers[:3]:
            short = ans[:140].rstrip()
            if short and short not in bullets:
                bullets.append(short)
        out["bullets"] = bullets[:6]
        return out


_service: ItemDeepenService | None = None


def get_item_deepen_service(settings: Settings | None = None) -> ItemDeepenService:
    global _service
    if _service is None or settings is not None:
        _service = ItemDeepenService(settings)
    return _service
