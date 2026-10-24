"""Optional web search for research_propose (Tavily when configured)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_TAVILY_URL = "https://api.tavily.com/search"
_TIMEOUT_S = 20.0


class WebSearchError(Exception):
    """Raised when research search fails in a user-visible way."""

    def __init__(self, message: str, *, code: str = "search_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class WebSearchService:
    """Thin Tavily client. No key → ``research_unavailable``."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def configured(self) -> bool:
        return bool((self.settings.tavily_api_key or "").strip())

    def search(self, query: str, *, max_results: int = 5) -> list[dict[str, Any]]:
        text = query.strip()
        if not text:
            raise WebSearchError(
                "Need a search query to research that claim.",
                code="empty_query",
            )
        if not self.configured():
            raise WebSearchError(
                "Web research is not configured. Set TAVILY_API_KEY on the "
                "server (optional), or use Edit mode for changes that do not "
                "need verification.",
                code="research_unavailable",
            )

        payload = {
            "api_key": self.settings.tavily_api_key.strip(),
            "query": text,
            "search_depth": "basic",
            "max_results": max(1, min(max_results, 8)),
            "include_answer": True,
        }
        try:
            with httpx.Client(timeout=_TIMEOUT_S) as client:
                response = client.post(_TAVILY_URL, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            logger.exception("tavily search failed")
            raise WebSearchError(
                "Web research failed. Try again in a moment.",
                code="search_failed",
            ) from exc

        results: list[dict[str, Any]] = []
        answer = data.get("answer")
        if isinstance(answer, str) and answer.strip():
            results.append({"title": "Tavily summary", "url": "", "content": answer})
        for item in data.get("results") or []:
            if not isinstance(item, dict):
                continue
            results.append(
                {
                    "title": str(item.get("title") or ""),
                    "url": str(item.get("url") or ""),
                    "content": str(item.get("content") or ""),
                }
            )
        return results


def get_web_search_service() -> WebSearchService:
    return WebSearchService()
