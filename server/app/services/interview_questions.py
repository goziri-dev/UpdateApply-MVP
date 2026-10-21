"""Generate calm conversation prompts for a parsed profile item via OpenRouter."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import Settings, get_settings
from app.core.llm_tasks import AgentTask
from app.schemas.interview import GeneratedInterviewScript
from app.services.agents import AgentFactory

logger = logging.getLogger(__name__)

MAX_QUESTIONS = 4
MIN_QUESTIONS = 2

# Bump when the system prompt / tone / script shape changes so cached
# ``item_scripts`` are discarded and regenerated.
INTERVIEW_SCRIPT_VERSION = 2

INTERVIEW_SYSTEM_PROMPT = """\
You are a calm career consultant helping someone flesh out ONE resume item
(a work role OR a project) in a low-pressure conversation.

Tone:
- Warm, curious, and non-judgmental — like a thoughtful consultant or therapist,
  not a recruiter or hiring manager.
- Invite honesty: fuzzy memory, shared credit, things they oversold on the resume,
  or things they undersold. Make it safe to talk openly; no pressure if they're unsure.
- Prefer open, reflective prompts over ownership/metrics interrogation.
- Avoid: "Walk me through", "Tell me about a time", STAR/behavioral framing,
  "prove", "candidate", "interview", grilling on metrics, or capture/evidence language.

Goals:
- Deepen the story so the career profile reflects what actually happened
  (what they did, how they worked, tools, outcomes) — specific to THIS item's
  company/title/summary/bullets, not generic templates.
- Do NOT treat skills as a separate conversation topic; skills stay on the resume extract.
- Respect a tight turn budget: 3–4 short spoken prompts total (answers of ~1–3 sentences).
- Coverage: 3–4 short soft theme labels the UI can check off. Prefer gentle wording
  (role examples: Day-to-day, How you worked, Tools, Outcomes; project examples:
  Why it exists, How you approached it, Tools, Where it stands). Adapt to what is
  thin or missing in the resume text.
- Clarify gently what was actually theirs vs the team's when that helps; ask what
  they'd want a friend to understand about the work.
- The LAST prompt must invite a soft wrap-up (e.g. anything else they'd like to add
  before moving on — no rush).
- Never invent employers, products, or metrics that are not hinted at in the item;
  you may gently ask them to fill gaps in their own words.
"""


class InterviewError(Exception):
    """Raised when interview question generation fails in a user-visible way."""

    def __init__(self, message: str, *, code: str = "interview_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class InterviewQuestionService:
    """Profile item → structured interview script via OpenRouter."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.agents = AgentFactory(self.settings)

    def generate_for_item(
        self,
        *,
        item: dict[str, Any],
        kind: Literal["role", "project"],
        basics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.agents.configured():
            raise InterviewError(
                "Interview questions are not configured. Set OPENROUTER_API_KEY on the server.",
                code="openrouter_unconfigured",
            )

        item_keys = (
            ("id", "company", "title", "start", "end", "summary", "bullets")
            if kind == "role"
            else ("id", "title", "start", "end", "summary", "bullets")
        )
        payload = {
            "kind": kind,
            "item": {k: item.get(k) for k in item_keys},
            "basics": {
                "name": (basics or {}).get("name") or "",
                "location": (basics or {}).get("location") or "",
            },
        }

        try:
            llm = self.agents.create(AgentTask.INTERVIEW_QUESTIONS)
            structured = llm.with_structured_output(GeneratedInterviewScript)
            result = structured.invoke(
                [
                    SystemMessage(content=INTERVIEW_SYSTEM_PROMPT),
                    HumanMessage(
                        content=(
                            "Generate calm conversation prompts (reflection questions) "
                            "for this resume item.\n"
                            f"Return kind={kind!r}.\n\n"
                            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
                        )
                    ),
                ]
            )
        except InterviewError:
            raise
        except Exception as exc:
            logger.exception("OpenRouter interview question generation failed")
            raise InterviewError(
                "Could not generate interview questions. Try again in a moment.",
                code="llm_failed",
            ) from exc

        script = self._coerce(result)
        return self._normalize_script(script, kind=kind, item=item)

    @staticmethod
    def _coerce(result: object) -> GeneratedInterviewScript:
        if isinstance(result, GeneratedInterviewScript):
            return result
        if isinstance(result, dict):
            return GeneratedInterviewScript.model_validate(result)
        raise InterviewError(
            "Interview question generation returned an unexpected shape. Try again.",
            code="invalid_interview",
        )

    @staticmethod
    def _default_label(kind: Literal["role", "project"], item: dict[str, Any]) -> str:
        if kind == "project":
            title = str(item.get("title") or "Project").strip() or "Project"
            return f"{title} (project)"
        title = str(item.get("title") or "Role").strip() or "Role"
        company = str(item.get("company") or "").strip()
        return f"{title} · {company}" if company else title

    def _normalize_script(
        self,
        script: GeneratedInterviewScript,
        *,
        kind: Literal["role", "project"],
        item: dict[str, Any],
    ) -> dict[str, Any]:
        label = (script.label or "").strip() or self._default_label(kind, item)
        resolved_kind: Literal["role", "project"] = (
            script.kind if script.kind in ("role", "project") else kind
        )
        coverage = list(script.coverage)[:MAX_QUESTIONS]
        questions = list(script.questions)[:MAX_QUESTIONS]

        if not coverage:
            coverage = (
                ["Day-to-day", "Tools", "Outcomes"]
                if resolved_kind == "role"
                else ["Why it exists", "How you approached it", "Outcomes"]
            )
        if len(questions) < MIN_QUESTIONS:
            raise InterviewError(
                "Interview question generation returned too few questions. Try again.",
                code="empty_interview",
            )

        # Ensure a soft wrap-up last prompt when the model forgot one.
        last = questions[-1].lower()
        if "anything else" not in last and "before we" not in last:
            wrap = (
                "Anything else you'd like to add about this before we move on? "
                "No rush if not."
            )
            if len(questions) < MAX_QUESTIONS:
                questions.append(wrap)
            else:
                questions[-1] = wrap

        return {
            "label": label,
            "kind": resolved_kind,
            "coverage": coverage,
            "questions": questions,
        }


def get_interview_question_service(
    settings: Settings | None = None,
) -> InterviewQuestionService:
    return InterviewQuestionService(settings=settings)
