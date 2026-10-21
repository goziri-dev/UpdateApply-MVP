"""OpenRouter task → default model mapping.

Enum *values* are stable task ids (unique). Default models live in
``DEFAULT_MODEL_BY_TASK`` so two tasks can share a cheap model without
StrEnum aliasing.
"""

from __future__ import annotations

from enum import StrEnum


class AgentTask(StrEnum):
    """Distinct LLM jobs for :class:`~app.services.agents.AgentFactory`."""

    RESUME_EXTRACT = "resume_extract"
    INTERVIEW_QUESTIONS = "interview_questions"
    PROFILE_REVIEW = "profile_review"
    RESUME_TAILOR = "resume_tailor"


# Cheap + capable OpenRouter slugs. Prefer Gemini Flash for extract / Q-gen
# (matches local OPENROUTER_MODEL). Review + tailor use gpt-4o-mini for a bit
# more judgment / writing quality while staying inexpensive.
DEFAULT_MODEL_BY_TASK: dict[AgentTask, str] = {
    AgentTask.RESUME_EXTRACT: "google/gemini-2.5-flash",
    AgentTask.INTERVIEW_QUESTIONS: "google/gemini-2.5-flash",
    AgentTask.PROFILE_REVIEW: "openai/gpt-4o-mini",
    AgentTask.RESUME_TAILOR: "openai/gpt-4o-mini",
}
