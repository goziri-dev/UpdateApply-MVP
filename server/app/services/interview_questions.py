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

# Separate from onboarding so post-onboarding deepen never recycles Day-to-day scripts.
DEEPEN_SCRIPT_VERSION = 1

DEEPEN_SYSTEM_PROMPT = """\
You write short follow-up questions that enrich ONE resume item AFTER onboarding.
This is NOT the first interview — the person already has a stub or remade item.

Tone:
- Calm consultant: warm, curious, specific. Not a recruiter or STAR interviewer.
- Prefer concrete, thoughtful prompts grounded in THIS item's bullets/summary.
- Avoid onboarding tropes entirely: no "typical day/week", "day-to-day look like",
  "walk me through your role", recycled Day-to-day / How you worked openers,
  "tell me about a time", ownership grilling, or generic wrap-ups as the only content.

Goals:
- Spot what is thin, vague, new, or underspecified in the current bullets/summary
  (missing scope, tools, collaborators, constraints, outcomes, what changed).
- Ask 2–4 NEW questions that would unlock richer, honest detail for the resume.
- Theme labels should feel specific to the gaps (e.g. "Scope you owned",
  "Tools in the loop", "What shifted", "Who you worked with") — not the
  onboarding defaults Day-to-day / Why it exists.
- NEVER repeat or paraphrase questions listed in prior_questions_to_avoid.
- Prefer angles not already covered in prior_themes_to_avoid.
- Last prompt may softly invite anything else — but only after novel questions.
- Do not invent employers, products, or metrics; ask them to fill gaps in their words.
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
        """Onboarding interview script (Day-to-day themes OK)."""
        return self._generate(
            item=item,
            kind=kind,
            basics=basics,
            system_prompt=INTERVIEW_SYSTEM_PROMPT,
            human_preamble=(
                "Generate calm conversation prompts (reflection questions) "
                "for this resume item.\n"
            ),
            deepen=False,
        )

    def generate_deepen_for_item(
        self,
        *,
        item: dict[str, Any],
        kind: Literal["role", "project"],
        basics: dict[str, Any] | None = None,
        prior_questions: list[str] | None = None,
        prior_themes: list[str] | None = None,
    ) -> dict[str, Any]:
        """Post-onboarding deepen script — novel Qs, excludes prior prompts."""
        return self._generate(
            item=item,
            kind=kind,
            basics=basics,
            system_prompt=DEEPEN_SYSTEM_PROMPT,
            human_preamble=(
                "Generate NEW deepen follow-ups for this resume item. "
                "Avoid onboarding tropes and anything in prior_questions_to_avoid.\n"
            ),
            deepen=True,
            prior_questions=prior_questions,
            prior_themes=prior_themes,
        )

    def _generate(
        self,
        *,
        item: dict[str, Any],
        kind: Literal["role", "project"],
        basics: dict[str, Any] | None,
        system_prompt: str,
        human_preamble: str,
        deepen: bool,
        prior_questions: list[str] | None = None,
        prior_themes: list[str] | None = None,
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
        payload: dict[str, Any] = {
            "kind": kind,
            "item": {k: item.get(k) for k in item_keys},
            "basics": {
                "name": (basics or {}).get("name") or "",
                "location": (basics or {}).get("location") or "",
            },
        }
        if deepen:
            payload["prior_questions_to_avoid"] = [
                str(q).strip() for q in (prior_questions or []) if str(q).strip()
            ][:48]
            payload["prior_themes_to_avoid"] = [
                str(t).strip() for t in (prior_themes or []) if str(t).strip()
            ][:32]
            payload["deepen_script_version"] = DEEPEN_SCRIPT_VERSION

        try:
            llm = self.agents.create(AgentTask.INTERVIEW_QUESTIONS)
            structured = llm.with_structured_output(GeneratedInterviewScript)
            result = structured.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(
                        content=(
                            f"{human_preamble}"
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
        normalized = self._normalize_script(script, kind=kind, item=item, deepen=deepen)
        if deepen:
            normalized = self._filter_echoed_priors(
                normalized,
                prior_questions=prior_questions or [],
            )
        return normalized

    @staticmethod
    def _filter_echoed_priors(
        script: dict[str, Any],
        *,
        prior_questions: list[str],
    ) -> dict[str, Any]:
        """Drop questions that too closely echo already-asked prompts."""
        priors = [str(p).strip().casefold() for p in prior_questions if str(p).strip()]
        if not priors:
            return script

        kept: list[str] = []
        for q in script.get("questions") or []:
            text = str(q).strip()
            if not text:
                continue
            low = text.casefold()
            if any(
                p == low or (len(p) > 24 and (p in low or low in p)) for p in priors
            ):
                continue
            kept.append(text)

        if len(kept) < MIN_QUESTIONS:
            # Keep originals if filter emptied the script; LLM already got the avoid list.
            return script
        out = dict(script)
        out["questions"] = kept[:MAX_QUESTIONS]
        return out

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
        deepen: bool = False,
    ) -> dict[str, Any]:
        label = (script.label or "").strip() or self._default_label(kind, item)
        resolved_kind: Literal["role", "project"] = (
            script.kind if script.kind in ("role", "project") else kind
        )
        coverage = list(script.coverage)[:MAX_QUESTIONS]
        questions = list(script.questions)[:MAX_QUESTIONS]

        if not coverage:
            if deepen:
                coverage = (
                    ["Scope you owned", "Tools in the loop", "What shifted"]
                    if resolved_kind == "role"
                    else ["What changed", "Your slice", "Constraints"]
                )
            else:
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
