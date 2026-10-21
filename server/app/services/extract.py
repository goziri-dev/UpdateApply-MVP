"""Resume PDF → structured Profile via pymupdf4llm + OpenRouter extract agent."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import Settings, get_settings
from app.core.llm_tasks import AgentTask
from app.schemas.extract import ExtractedProfile
from app.services.agents import AgentFactory
from app.services.pdf import pdf_bytes_to_markdown

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM_PROMPT = """\
You extract a structured career profile from a resume provided as Markdown.

Rules:
- Use only facts present in the resume. Do not invent employers, degrees, skills, dates, or links.
- If a field is missing, leave it empty (empty string or empty list) — never invent placeholders.
- Prefer concise summaries and bullet lists pulled from the resume wording.
- For experience and projects, leave ``id`` empty; the server will assign stable ids.
- Skills: group related keywords (e.g. Languages, Backend) when the resume suggests groups;
  otherwise use a single group named "Skills".
- Dates may be years or year-month strings as written on the resume.
"""


class ExtractError(Exception):
    """Raised when PDF→profile extract fails in a user-visible way."""

    def __init__(self, message: str, *, code: str = "extract_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ResumeExtractService:
    """PDF bytes → markdown → OpenRouter structured Profile."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.agents = AgentFactory(self.settings)

    def extract_from_pdf_bytes(
        self,
        data: bytes,
        *,
        filename: str = "resume.pdf",
        email_hint: str | None = None,
    ) -> dict[str, Any]:
        if not data:
            raise ExtractError(
                "No PDF content to parse. Upload a resume first.",
                code="empty_pdf",
            )
        if not self.agents.configured():
            raise ExtractError(
                "Resume extract is not configured. Set OPENROUTER_API_KEY on the server.",
                code="openrouter_unconfigured",
            )

        try:
            markdown = pdf_bytes_to_markdown(data, filename=filename)
        except Exception as exc:
            logger.exception("PDF markdown conversion failed")
            raise ExtractError(
                "Could not read this PDF. Export a text-based PDF resume and try again.",
                code="pdf_unreadable",
            ) from exc

        if not markdown.strip():
            raise ExtractError(
                "No text found in this PDF. Use a text resume (not a scanned image) and try again.",
                code="empty_text",
            )

        try:
            llm = self.agents.create(AgentTask.RESUME_EXTRACT)
            structured = llm.with_structured_output(ExtractedProfile)
            hint = (
                f"\nAccount email hint (use only if the resume omits email): {email_hint}"
                if email_hint
                else ""
            )
            result = structured.invoke(
                [
                    SystemMessage(content=EXTRACT_SYSTEM_PROMPT),
                    HumanMessage(
                        content=(
                            "Extract the career profile from this resume Markdown.\n"
                            f"{hint}\n\n---\n{markdown}\n---"
                        )
                    ),
                ]
            )
        except ExtractError:
            raise
        except Exception as exc:
            logger.exception("OpenRouter resume extract failed")
            raise ExtractError(
                "Resume extract failed. Try again in a moment, or re-upload a clearer PDF.",
                code="llm_failed",
            ) from exc

        profile = self._coerce_extracted(result)
        if profile.is_empty():
            raise ExtractError(
                "Could not extract a usable profile from this resume. "
                "Check that the PDF lists your name and work history, then try again.",
                code="empty_extract",
            )
        return profile.to_profile_dict()

    @staticmethod
    def _coerce_extracted(result: object) -> ExtractedProfile:
        if isinstance(result, ExtractedProfile):
            return result
        if isinstance(result, dict):
            return ExtractedProfile.model_validate(result)
        raise ExtractError(
            "Resume extract returned an unexpected shape. Try again.",
            code="invalid_extract",
        )


def get_resume_extract_service(
    settings: Settings | None = None,
) -> ResumeExtractService:
    return ResumeExtractService(settings=settings)
