"""Structured LLM output for interview question generation (TSK-13)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GeneratedInterviewScript(BaseModel):
    """One role/project conversation: soft coverage themes + reflection prompts."""

    label: str = Field(
        description="Short display label, e.g. 'Software Engineer · Acme' or 'UpdateApply (project)'."
    )
    kind: Literal["role", "project"] = "role"
    coverage: list[str] = Field(
        default_factory=list,
        description=(
            "3–4 soft theme labels to track (e.g. Day-to-day, Tools, Outcomes)."
        ),
    )
    questions: list[str] = Field(
        default_factory=list,
        description=(
            "3–4 calm, open reflection prompts for spoken answers; "
            "last invites anything else / soft wrap-up."
        ),
    )

    @field_validator("coverage", "questions")
    @classmethod
    def _strip_nonempty(cls, value: list[str]) -> list[str]:
        return [str(v).strip() for v in value if str(v).strip()]
