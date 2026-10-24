"""Agentic resume edit harness: edit / advise / research_propose + session memory."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import Settings, get_settings
from app.core.llm_tasks import AgentTask
from app.schemas.resume import (
    ResumeAdviseModel,
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
  facts you need in `detail`. (Research+propose can verify public company names.)
- Preserve existing item `id` values. New rows may use empty `id` (server assigns).
- Apply the instruction as fully as possible without inventing facts.

Return the complete document, not a partial patch.
"""

ADVISE_SYSTEM_PROMPT = """\
You are a resume coach for the user's current ResumeDocument. Answer their
question clearly and practically. Do NOT rewrite or return a ResumeDocument.

Inputs (JSON): resume, instruction (the question), prior_turns (session context).

Output: ResumeAdviseModel with `answer` only.

Guidance:
- Prefer region-aware norms when asked (e.g. US vs EU professional summary).
- Ground advice in what is actually on their resume when relevant.
- If they ask you to change the resume, explain what you would do and tell them
  to switch to Edit (or Research+propose) mode to apply it — do not emit JSON
  edits here.
"""

RESEARCH_SYSTEM_PROMPT = """\
You propose a ResumeDocument change after reviewing web research results for a
user claim (e.g. adding an employer they named, correcting a company spelling).

Inputs (JSON):
1. resume — current ResumeDocument.
2. instruction — what the user wants (often “add X” / verify a name).
3. research — search snippets (title, url, content). May be incomplete.
4. prior_turns — session context.

Output: ResumeEditProposalModel with:
- resume — proposed document (minimal diffs; preserve formats as in edit mode)
- detail — short summary of the proposal for the user
- confidence — 0.0–1.0 based on how well research supports the claim
- research_notes — brief what you verified (or could not verify)

Honesty with research:
- Public facts from research (company name existence, official spelling, rough
  industry) MAY be used to propose adding or correcting an employer/school the
  user claimed.
- Still do NOT invent metrics, achievements, titles, or employment dates the
  user did not provide. If they only said “add Outlier”, add a sparse experience
  entry (company name from research; empty/placeholder title/dates/bullets only
  if the user did not supply them — prefer leaving title/dates empty strings
  rather than fabricating).
- If research is weak or contradictory, keep confidence low, prefer not adding
  dubious facts, and explain in detail/research_notes.
- Preserve unrelated fields exactly (same date-format rules as edit mode).
"""

_EDIT_TIMEOUT_MS = 90_000


class ResumeEditError(Exception):
    """Raised when NL edit fails in a user-visible way."""

    def __init__(self, message: str, *, code: str = "edit_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ResumeEditService:
    """Propose edits / advice / researched proposals with session memory."""

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
            if mode is ResumeEditMode.ADVISE:
                response = self._advise(session, resume=resume, instruction=text)
            elif mode is ResumeEditMode.RESEARCH_PROPOSE:
                response = self._research_propose(
                    session, resume=resume, instruction=text
                )
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

    def _advise(
        self,
        session: EditSession,
        *,
        resume: ResumeDocument,
        instruction: str,
    ) -> ResumeEditResponse:
        llm = self.agents.create(
            AgentTask.RESUME_EDIT,
            timeout=_EDIT_TIMEOUT_MS,
        )
        structured = llm.with_structured_output(ResumeAdviseModel)
        payload = {
            "resume": resume.model_dump(),
            "instruction": instruction,
            "prior_turns": self.sessions.transcript_for_prompt(session),
        }
        result = structured.invoke(
            [
                SystemMessage(content=ADVISE_SYSTEM_PROMPT),
                HumanMessage(content=json.dumps(payload)),
            ]
        )
        answer = self._coerce_advise(result)
        response = ResumeEditResponse(
            resume=resume,
            stub=False,
            detail=answer.answer,
            mode=ResumeEditMode.ADVISE,
            session_id=session.session_id,
            applied=False,
        )
        self._record_turn(
            session,
            user_content=instruction,
            mode=ResumeEditMode.ADVISE,
            assistant_content=answer.answer,
            pending=None,
        )
        return response

    def _research_propose(
        self,
        session: EditSession,
        *,
        resume: ResumeDocument,
        instruction: str,
    ) -> ResumeEditResponse:
        hits = self.search.search(instruction)
        proposal = self._invoke_proposal(
            system=RESEARCH_SYSTEM_PROMPT,
            payload={
                "resume": resume.model_dump(),
                "instruction": instruction,
                "research": hits,
                "prior_turns": self.sessions.transcript_for_prompt(session),
            },
        )
        return self._finish_proposal(
            session,
            mode=ResumeEditMode.RESEARCH_PROPOSE,
            instruction=instruction,
            proposal=proposal,
            applied=True,
        )

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
        if mode is ResumeEditMode.RESEARCH_PROPOSE and proposal.research_notes:
            detail = f"{detail}\n\nResearch: {proposal.research_notes.strip()}"
        response = ResumeEditResponse(
            resume=proposal.resume,
            stub=False,
            detail=detail,
            mode=mode,
            session_id=session.session_id,
            applied=applied,
            confidence=proposal.confidence,
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

    def _coerce_advise(self, result: object) -> ResumeAdviseModel:
        if isinstance(result, ResumeAdviseModel):
            return result
        if isinstance(result, dict):
            return ResumeAdviseModel.model_validate(result)
        raise ResumeEditError(
            "Model returned an unexpected advice shape.",
            code="invalid_result",
        )


def get_resume_edit_service() -> ResumeEditService:
    return ResumeEditService()
