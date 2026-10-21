"""Structured LLM output for interview question generation (TSK-13)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GeneratedInterviewScript(BaseModel):
    """One role/project interview: coverage checklist + guided questions."""

    label: str = Field(
        description="Short display label, e.g. 'Software Engineer · Acme' or 'UpdateApply (project)'."
    )
    kind: Literal["role", "project"] = "role"
    coverage: list[str] = Field(
        default_factory=list,
        description="3–4 coverage themes to track (e.g. Scope, Stack, Impact).",
    )
    questions: list[str] = Field(
        default_factory=list,
        description="3–4 guided follow-up questions; last invites anything else / wrap-up.",
    )

    @field_validator("coverage", "questions")
    @classmethod
    def _strip_nonempty(cls, value: list[str]) -> list[str]:
        return [str(v).strip() for v in value if str(v).strip()]
