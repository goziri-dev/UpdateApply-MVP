"""Create OpenRouter chat clients keyed by :class:`~app.core.llm_tasks.AgentTask`.

Do not hardcode one model for every job — call ``AgentFactory.create(task)``.
"""

from __future__ import annotations

from typing import Any

from langchain_openrouter import ChatOpenRouter

from app.core.config import Settings, get_settings
from app.core.llm_tasks import DEFAULT_MODEL_BY_TASK, AgentTask

_TASK_OVERRIDE_ATTR: dict[AgentTask, str] = {
    AgentTask.RESUME_EXTRACT: "openrouter_model_resume_extract",
    AgentTask.INTERVIEW_QUESTIONS: "openrouter_model_interview_questions",
    AgentTask.PROFILE_REVIEW: "openrouter_model_profile_review",
    AgentTask.RESUME_TAILOR: "openrouter_model_resume_tailor",
    AgentTask.RESUME_EDIT: "openrouter_model_resume_edit",
    AgentTask.TITLE_SUGGESTIONS: "openrouter_model_title_suggestions",
    AgentTask.EMBEDDING: "openrouter_model_embedding",
}


class AgentFactory:
    """Build a :class:`ChatOpenRouter` for a specific task's model."""

    # langchain_openrouter uses milliseconds. Default SDK timeout is None
    # (wait forever) — that freezes sync /parse when a provider stalls.
    DEFAULT_TIMEOUT_MS = 60_000

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def model_for(self, task: AgentTask) -> str:
        """Resolve OpenRouter model id: env override if set, else task default."""
        attr = _TASK_OVERRIDE_ATTR[task]
        override = getattr(self.settings, attr, "") or ""
        if isinstance(override, str) and override.strip():
            return override.strip()
        return DEFAULT_MODEL_BY_TASK[task]

    def configured(self) -> bool:
        return self.settings.openrouter_configured

    def create(self, task: AgentTask, **kwargs: Any) -> ChatOpenRouter:
        """Return a chat model for ``task``.

        Raises:
            RuntimeError: when ``OPENROUTER_API_KEY`` is missing, or when
            ``task`` is :attr:`~AgentTask.EMBEDDING` (use EmbeddingsClient).
        """
        if task is AgentTask.EMBEDDING:
            raise RuntimeError(
                "AgentTask.EMBEDDING is not a chat model; use EmbeddingsClient."
            )
        if not self.configured():
            raise RuntimeError(
                "OPENROUTER_API_KEY is not configured; cannot create an OpenRouter agent."
            )
        # Bound hangs: ChatOpenRouter.request_timeout default is None.
        kwargs.setdefault("timeout", self.DEFAULT_TIMEOUT_MS)
        return ChatOpenRouter(
            model=self.model_for(task),
            api_key=self.settings.openrouter_api_key,
            app_title=self.settings.app_name,
            **kwargs,
        )

    def describe_models(self) -> dict[str, str]:
        """Task name → resolved model (for health / debug notes)."""
        return {task.name: self.model_for(task) for task in AgentTask}


def get_agent_factory(settings: Settings | None = None) -> AgentFactory:
    return AgentFactory(settings=settings)
