"""Agentic resume harness: edit / ask (resume + live web search) + session memory."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import Settings, get_settings
from app.core.llm_tasks import AgentTask
from app.schemas.resume import (
    ResumeAskModel,
    ResumeDocument,
    ResumeEditMode,
    ResumeEditOutcome,
    ResumeEditProposalModel,
    ResumeEditResponse,
)
from app.services.agents import AgentFactory
from app.services.edit_session import EditSession, EditTurn, get_edit_session_store
from app.services.web_search import WebSearchError, get_web_search_service

logger = logging.getLogger(__name__)

EDIT_SYSTEM_PROMPT = """\
You edit an existing ResumeDocument based on a short natural-language instruction
and optional prior turn context from this edit session.

Inputs (JSON):
1. resume — the current ResumeDocument (source of truth for content).
2. instruction — what the user wants changed this turn.
3. prior_turns — earlier instructions, assistant summaries, and accept/reject
   outcomes in this session (may be empty). Use them for continuity
   (e.g. “also shorten that bullet” refers to the last touched bullet).

Output: ResumeEditProposalModel — full ResumeDocument after the edit, plus a
short human-readable `detail` summarizing what changed (1–3 sentences).

Minimal-diff rules (critical):
- Change ONLY what the instruction targets. Leave every other field byte-for-byte
  identical when possible (same strings, order, punctuation, whitespace style).
- Preserve field formats. Dates that include a month (e.g. "Nov 2022", "03/2021")
  MUST keep that month/day structure when only the year (or another part) changes
  — e.g. "change start year to 2021" on "Nov 2022" → "Nov 2021", never bare "2021".
- Preserve links, punctuation, bullet voice, and section structure. Do not
  “normalize”, title-case, reformat, or tidy unrelated fields.
- Do not reorder lists unless the instruction asks to reorder.

Honesty:
- Do NOT invent metrics, achievements, degrees, tools, titles, or dates that are
  not already present or clearly implied by the instruction applying to existing
  content.
- Adding a job/employer/project from **user-authored facts is allowed** in edit
  mode when the instruction clearly supplies them (company, title, dates, and/or
  bullets the user stated). Insert a new experience/project row with only those
  facts — leave other fields empty strings rather than fabricating metrics or
  achievements they did not provide. Prefer a sparse stub over inventing detail.
- Do NOT invent employers/schools the user never named. If they ask to “add a
  role” with no company/title/facts, leave the document unchanged and say what
  facts you need in `detail`. (Ask mode can look up public company info on the
  web; then tell Edit the facts you want applied.)
- Preserve existing item `id` values. New rows may use empty `id` (server assigns).
- Apply the instruction as fully as possible without inventing facts.

Return the complete document, not a partial patch.
"""

ASK_SYSTEM_PROMPT = """\
You answer the user's question about their career, resume, or employers using
BOTH their current ResumeDocument and live web research results. Do NOT rewrite
or return a ResumeDocument.

Inputs (JSON):
1. resume — current ResumeDocument (source of truth for what they did).
2. instruction — the question.
3. search_query — the grounded query that was sent to web search.
4. research — search snippets (title, url, content). May be empty/incomplete.
5. research_warning — optional note when live search failed; treat research as
   unavailable and keep confidence low for public company facts.
6. prior_turns — session context.

Output: ResumeAskModel with:
- answer — clear, practical answer (short paragraphs; no JSON edits)
- confidence — 0.0–1.0 based on how well research + resume support the answer
- research_notes — brief what research verified, or could not verify (mention
  source sites by name when helpful)

Guidance:
- Use research for public facts (what a company does, industry norms, region
  conventions). Use the resume for what the user actually did — never present
  web facts as the user's own achievements.
- When the question names an employer or school on the resume, connect the
  answer to that role (title, dates) where it helps.
- If research is weak, empty, or contradictory, say so, keep confidence low,
  and do not guess company facts.
- Prefer region-aware norms when asked (e.g. US vs EU professional summary).
- If they ask you to change the resume, answer briefly (what you would change)
  and tell them to switch to Edit to apply it — do not emit JSON edits here.
"""

_EDIT_TIMEOUT_MS = 90_000
_MAX_QUERY_CHARS = 380  # Tavily caps queries at ~400 chars.
_ORG_STOPWORDS = frozenset(
    {"inc", "ltd", "llc", "limited", "the", "and", "corp", "group", "company"}
)


class ResumeEditError(Exception):
    """Raised when NL edit fails in a user-visible way."""

    def __init__(self, message: str, *, code: str = "edit_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ResumeEditService:
    """Propose edits / answer questions (Ask) with session memory."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.agents = AgentFactory(self.settings)
        self.sessions = get_edit_session_store()
        self.search = get_web_search_service()

    def propose(
        self,
        *,
        user_id: UUID,
        resume: ResumeDocument,
        instruction: str,
        mode: ResumeEditMode = ResumeEditMode.EDIT,
        session_id: str | None = None,
        prior_outcome: ResumeEditOutcome | None = None,
    ) -> ResumeEditResponse:
        text = instruction.strip()
        if not text:
            raise ResumeEditError(
                "Describe what to change before proposing edits.",
                code="empty_instruction",
            )

        # Ask must go to the web — fail loudly (before stub/LLM) when unconfigured.
        if mode is ResumeEditMode.ASK and not self.search.configured():
            raise ResumeEditError(
                "Ask uses live web search, which isn’t configured. Set "
                "TAVILY_API_KEY on the server, or use Edit for changes that "
                "don’t need verification.",
                code="research_unavailable",
            )

        session = self.sessions.get_or_create(
            user_id=user_id,
            session_id=session_id,
        )
        self._apply_prior_outcome(session, prior_outcome)

        if not self.agents.configured():
            if self.settings.allow_stub_parse:
                stub = ResumeEditResponse(
                    resume=resume,
                    stub=True,
                    detail=(
                        "Stub edit: OpenRouter off — returned your document "
                        "unchanged (ALLOW_STUB_PARSE)."
                    ),
                    mode=mode,
                    session_id=session.session_id,
                    applied=False,
                )
                self._record_turn(
                    session,
                    user_content=text,
                    mode=mode,
                    assistant_content=stub.detail or "",
                    pending=None,
                )
                return stub
            raise ResumeEditError(
                "OpenRouter is not configured; cannot propose resume edits.",
                code="openrouter_missing",
            )

        try:
            if mode is ResumeEditMode.ASK:
                response = self._ask(session, resume=resume, instruction=text)
            else:
                response = self._edit(session, resume=resume, instruction=text)
        except ResumeEditError:
            raise
        except WebSearchError as exc:
            raise ResumeEditError(exc.message, code=exc.code) from exc
        except Exception as exc:
            logger.exception("resume edit failed mode=%s", mode)
            raise ResumeEditError(
                "Couldn’t propose edits. Try again in a moment.",
                code="edit_failed",
            ) from exc

        return response

    def clear_session(self, *, user_id: UUID, session_id: str) -> bool:
        return self.sessions.delete(user_id=user_id, session_id=session_id)

    def _apply_prior_outcome(
        self,
        session: EditSession,
        prior_outcome: ResumeEditOutcome | None,
    ) -> None:
        if prior_outcome is None:
            return
        note = (
            "User accepted the last proposal into the form (not yet saved)."
            if prior_outcome is ResumeEditOutcome.ACCEPTED
            else "User rejected the last proposal; resume stayed as before."
        )
        self.sessions.append_turn(
            session,
            EditTurn(
                role="outcome",
                content=note,
                mode="edit",
                outcome=prior_outcome.value,
            ),
        )
        if prior_outcome is ResumeEditOutcome.REJECTED:
            self.sessions.set_pending(session, None)

    def _edit(
        self,
        session: EditSession,
        *,
        resume: ResumeDocument,
        instruction: str,
    ) -> ResumeEditResponse:
        proposal = self._invoke_proposal(
            system=EDIT_SYSTEM_PROMPT,
            payload={
                "resume": resume.model_dump(),
                "instruction": instruction,
                "prior_turns": self.sessions.transcript_for_prompt(session),
            },
        )
        return self._finish_proposal(
            session,
            mode=ResumeEditMode.EDIT,
            instruction=instruction,
            proposal=proposal,
            applied=True,
        )

    def _ask(
        self,
        session: EditSession,
        *,
        resume: ResumeDocument,
        instruction: str,
    ) -> ResumeEditResponse:
        query = self._build_search_query(resume, instruction)
        research_warning: str | None = None
        try:
            hits = self.search.search(query)
        except WebSearchError as exc:
            # Unconfigured / empty query stay hard failures; live search
            # outages must not brick the Ask turn — answer from the resume.
            if exc.code in {"research_unavailable", "empty_query"}:
                raise
            logger.warning(
                "ask web search failed code=%s; answering from resume only",
                exc.code,
            )
            hits = []
            research_warning = (
                "Live web research was unavailable for this turn; answer is "
                "based on the resume only."
            )
        llm = self.agents.create(
            AgentTask.RESUME_EDIT,
            timeout=_EDIT_TIMEOUT_MS,
        )
        structured = llm.with_structured_output(ResumeAskModel)
        payload = {
            "resume": resume.model_dump(),
            "instruction": instruction,
            "search_query": query,
            "research": hits,
            "research_warning": research_warning,
            "prior_turns": self.sessions.transcript_for_prompt(session),
        }
        result = structured.invoke(
            [
                SystemMessage(content=ASK_SYSTEM_PROMPT),
                HumanMessage(content=json.dumps(payload)),
            ]
        )
        answer = self._coerce_ask(result)
        detail = answer.answer.strip()
        if answer.research_notes and answer.research_notes.strip():
            detail = f"{detail}\n\nResearch: {answer.research_notes.strip()}"
        if research_warning:
            detail = f"{detail}\n\n{research_warning}"
        response = ResumeEditResponse(
            resume=resume,
            stub=False,
            detail=detail,
            mode=ResumeEditMode.ASK,
            session_id=session.session_id,
            applied=False,
            confidence=answer.confidence,
        )
        self._record_turn(
            session,
            user_content=instruction,
            mode=ResumeEditMode.ASK,
            assistant_content=detail,
            pending=None,
        )
        return response

    def _build_search_query(self, resume: ResumeDocument, instruction: str) -> str:
        """Enrich the question with resume context for any employer/school it names.

        e.g. “Tell me about IPN” → “Tell me about IPN — IPN, Product Designer,
        Jan 2022–Mar 2023”. Falls back to the bare question when nothing matches.
        """
        lowered = instruction.lower()
        context: list[str] = []
        for item in resume.experience:
            if self._names_org(lowered, item.company):
                dates = " – ".join(p for p in (item.start, item.end) if p.strip())
                context.append(
                    ", ".join(p for p in (item.company, item.title, dates) if p.strip())
                )
        for edu in resume.education:
            if self._names_org(lowered, edu.school):
                context.append(
                    ", ".join(p for p in (edu.school, edu.degree) if p.strip())
                )
        if not context:
            return instruction[:_MAX_QUERY_CHARS]
        grounded = f"{instruction} — {'; '.join(context)}"
        return grounded[:_MAX_QUERY_CHARS]

    @staticmethod
    def _names_org(lowered_instruction: str, name: str) -> bool:
        """True when the instruction mentions the org (full name or a distinct word)."""
        full = name.strip().lower()
        if not full:
            return False
        if re.search(rf"\b{re.escape(full)}\b", lowered_instruction):
            return True
        for token in re.findall(r"[a-z0-9&]+", full):
            if len(token) < 3 or token in _ORG_STOPWORDS:
                continue
            if re.search(rf"\b{re.escape(token)}\b", lowered_instruction):
                return True
        return False

    def _invoke_proposal(
        self,
        *,
        system: str,
        payload: dict[str, Any],
    ) -> ResumeEditProposalModel:
        llm = self.agents.create(
            AgentTask.RESUME_EDIT,
            timeout=_EDIT_TIMEOUT_MS,
        )
        structured = llm.with_structured_output(ResumeEditProposalModel)
        result = structured.invoke(
            [
                SystemMessage(content=system),
                HumanMessage(content=json.dumps(payload)),
            ]
        )
        return self._coerce_proposal(result)

    def _finish_proposal(
        self,
        session: EditSession,
        *,
        mode: ResumeEditMode,
        instruction: str,
        proposal: ResumeEditProposalModel,
        applied: bool,
    ) -> ResumeEditResponse:
        detail = (proposal.detail or "").strip() or "Proposed changes ready to review."
        response = ResumeEditResponse(
            resume=proposal.resume,
            stub=False,
            detail=detail,
            mode=mode,
            session_id=session.session_id,
            applied=applied,
        )
        pending = proposal.resume.model_dump() if applied else None
        self._record_turn(
            session,
            user_content=instruction,
            mode=mode,
            assistant_content=detail,
            pending=pending,
        )
        return response

    def _record_turn(
        self,
        session: EditSession,
        *,
        user_content: str,
        mode: ResumeEditMode | str,
        assistant_content: str,
        pending: dict[str, Any] | None,
    ) -> None:
        mode_value = mode.value if isinstance(mode, ResumeEditMode) else mode
        self.sessions.append_turn(
            session,
            EditTurn(role="user", content=user_content, mode=mode_value),
        )
        self.sessions.append_turn(
            session,
            EditTurn(role="assistant", content=assistant_content, mode=mode_value),
        )
        self.sessions.set_pending(session, pending)

    def _coerce_proposal(self, result: object) -> ResumeEditProposalModel:
        if isinstance(result, ResumeEditProposalModel):
            return result
        if isinstance(result, dict):
            return ResumeEditProposalModel.model_validate(result)
        raise ResumeEditError(
            "Model returned an unexpected edit shape.",
            code="invalid_result",
        )

    def _coerce_ask(self, result: object) -> ResumeAskModel:
        if isinstance(result, ResumeAskModel):
            return result
        if isinstance(result, dict):
            return ResumeAskModel.model_validate(result)
        raise ResumeEditError(
            "Model returned an unexpected answer shape.",
            code="invalid_result",
        )


def get_resume_edit_service() -> ResumeEditService:
    return ResumeEditService()
