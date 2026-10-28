"""Rewrite an evergreen master resume from parse + interview transcripts."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import Settings, get_settings
from app.core.llm_tasks import AgentTask
from app.schemas.extract import ExtractedProfile
from app.services.agents import AgentFactory

logger = logging.getLogger(__name__)

# Bump when the rewrite prompt / output contract changes so cached remakes
# under ``_onboarding.review_version`` are discarded and regenerated.
PROFILE_REVIEW_VERSION = 2

PROFILE_REVIEW_SYSTEM_PROMPT = """\
You rewrite a candidate's evergreen master resume / career profile.

Inputs you receive:
1. The structured profile extracted from their uploaded resume (source of truth).
2. Clarifying conversation transcripts (Q&A) about roles and projects.
3. Soft coverage themes that were discussed.

This product serves every profession. Stay role-agnostic: nurse, PM, sales,
designer, trades, backend, clinical, academic, etc. Mirror the candidate's
own domain language. Do not invent a target persona or rewrite them into a
different career brand.

Preserve-first (default):
- Keep source role titles and domain wording exactly as used in the parse
  (and interview corrections). Do not dilute a specialized/niche title into a
  generic umbrella title, and do not invent a more "impressive" title either.
  Wrong across fields alike: niche clinical title → "Healthcare Worker";
  "Senior ICU Nurse" → "Nurse"; "Enterprise AE" → "Sales"; specialized eng
  title → "Full Stack Developer". Preserve the precise source title unless
  the conversation clearly corrects it.
- Prefer the parse's wording, structure, and density. Interview answers enrich
  existing bullets and role/project summaries — they do not replace a solid
  parse with a thinner rewrite.
- Keep roughly the same number of bullets per role/project when the source is
  already dense; add only when the conversation supplies a distinct, concrete
  fact that belongs as its own bullet.
- Preserve quantitative metrics, tools/systems/domain terms, and project or
  role status lines from the parse unless the conversation corrects them.

Your job:
- Produce a hireable evergreen master resume JSON in a clear, hireable,
  concrete resume voice (not a software/"technical-only" voice): concrete
  verbs, scope, tools/methods, and outcomes drawn from the source +
  interview — not marketing copy.
- Weave clarifying answers into existing bullets and summaries (not a dump of
  spoken answers, not a Q&A transcript, not a light "consistency pass").
- Keep structure matching the input schema (basics, summary, skills,
  experience, education, projects).
- Preserve real employers, titles, schools, dates, and links from the parse
  unless the conversation clearly corrects them.
- Prefer empty top-level `summary` (`""`) unless the conversation clearly
  needs a short positioning line (visa/relocation/work-auth, target-role
  clarity, or similar). Do NOT invent a generic career-branding summary when
  the parse had none or only a thin one.
- Ban soft/marketing adjectives and spoken intros. Never open with phrases
  like "Driven and innovative…", "Passionate caregiver…", "Results-oriented
  professional…", "Dynamic team player…", or "In my role as…". Write as a
  resume, not a cover letter or spoken answer.
- Prefer concrete verbs, scope, tools/methods, and outcomes when the
  conversation supplies them; keep resume wording when conversation is thin.
- Honesty: do NOT invent employers, dates, metrics, products, degrees, or
  tools that are not supported by the resume extract or the conversation.
- Skills: refine grouping/keywords from the resume; do not invent skill domains
  the person never mentioned. Conversation may add tools/methods they confirmed.
- Experience/project ids: keep the same ids as the input when present.
- Leave interviewed flags out of your reasoning; the server will restore them.
"""


class ProfileReviewError(Exception):
    """Raised when master-resume rewrite fails in a user-visible way."""

    def __init__(self, message: str, *, code: str = "review_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ProfileReviewService:
    """Parse + interview transcripts → remade master profile via OpenRouter."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.agents = AgentFactory(self.settings)

    def rewrite(
        self,
        *,
        parsed_profile: dict[str, Any],
        item_transcripts: dict[str, list[dict[str, Any]]],
        coverage_hits: dict[str, list[str]] | None = None,
        item_scripts: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.agents.configured():
            raise ProfileReviewError(
                "Profile rewrite is not configured. Set OPENROUTER_API_KEY on the server.",
                code="openrouter_unconfigured",
            )

        payload = {
            "parsed_profile": parsed_profile,
            "conversation": {
                "item_transcripts": item_transcripts,
                "coverage_hits": coverage_hits or {},
                "item_labels": {
                    item_id: (script or {}).get("label")
                    for item_id, script in (item_scripts or {}).items()
                    if isinstance(script, dict)
                },
            },
        }

        try:
            llm = self.agents.create(AgentTask.PROFILE_REVIEW)
            structured = llm.with_structured_output(ExtractedProfile)
            result = structured.invoke(
                [
                    SystemMessage(content=PROFILE_REVIEW_SYSTEM_PROMPT),
                    HumanMessage(
                        content=(
                            "Rewrite this into a preserve-first evergreen master "
                            "resume JSON.\n"
                            "Keep source titles, metrics, and bullet density; weave "
                            "interview answers into existing bullets.\n"
                            "Prefer empty summary unless positioning is clearly "
                            "needed. Do not invent unverifiable facts. Do not "
                            "return a Q&A dump.\n\n"
                            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
                        )
                    ),
                ]
            )
        except ProfileReviewError:
            raise
        except Exception as exc:
            logger.exception("OpenRouter profile rewrite failed")
            raise ProfileReviewError(
                "Could not rewrite your resume. Try again in a moment.",
                code="llm_failed",
            ) from exc

        remade = self._coerce(result)
        if remade.is_empty():
            raise ProfileReviewError(
                "Resume rewrite returned an empty profile. Try again.",
                code="empty_review",
            )
        return remade.to_profile_dict()

    @staticmethod
    def _coerce(result: object) -> ExtractedProfile:
        if isinstance(result, ExtractedProfile):
            return result
        if isinstance(result, dict):
            return ExtractedProfile.model_validate(result)
        raise ProfileReviewError(
            "Resume rewrite returned an unexpected shape. Try again.",
            code="invalid_review",
        )


def get_profile_review_service(
    settings: Settings | None = None,
) -> ProfileReviewService:
    return ProfileReviewService(settings=settings)
