"""OpenRouter embeddings client (AgentTask.EMBEDDING model resolution)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.llm_tasks import AgentTask
from app.models.profile_chunk import EMBEDDING_DIMENSIONS
from app.services.agents import AgentFactory

logger = logging.getLogger(__name__)

OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"
# Batch size keeps request payloads reasonable for remade-profile chunk counts.
_EMBED_BATCH_SIZE = 64


class EmbeddingError(Exception):
    """Raised when OpenRouter embeddings fail in a user-visible way."""

    def __init__(self, message: str, *, code: str = "embed_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class EmbeddingsClient:
    """Embed text via OpenRouter ``/api/v1/embeddings``."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.agents = AgentFactory(self.settings)
        self.dimensions = EMBEDDING_DIMENSIONS

    def configured(self) -> bool:
        return self.agents.configured()

    def model(self) -> str:
        return self.agents.model_for(AgentTask.EMBEDDING)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.configured():
            raise EmbeddingError(
                "Embeddings are not configured. Set OPENROUTER_API_KEY on the server.",
                code="openrouter_unconfigured",
            )

        cleaned = [t.strip() for t in texts]
        if any(not t for t in cleaned):
            raise EmbeddingError(
                "Cannot embed empty text chunks.",
                code="empty_text",
            )

        out: list[list[float]] = []
        for start in range(0, len(cleaned), _EMBED_BATCH_SIZE):
            batch = cleaned[start : start + _EMBED_BATCH_SIZE]
            out.extend(self._embed_batch(batch))
        return out

    def embed_query(self, text: str) -> list[float]:
        vectors = self.embed_texts([text])
        return vectors[0]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "X-Title": self.settings.app_name,
        }
        payload: dict[str, Any] = {
            "model": self.model(),
            "input": texts if len(texts) > 1 else texts[0],
            "dimensions": self.dimensions,
            "encoding_format": "float",
        }
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    OPENROUTER_EMBEDDINGS_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPStatusError as exc:
            logger.exception("OpenRouter embeddings HTTP error")
            detail = ""
            try:
                detail = str(exc.response.json())
            except ValueError, TypeError, KeyError:
                detail = exc.response.text[:200]
            raise EmbeddingError(
                f"Embedding request failed ({exc.response.status_code}). {detail}".strip(),
                code="llm_failed",
            ) from exc
        except Exception as exc:
            logger.exception("OpenRouter embeddings request failed")
            raise EmbeddingError(
                "Embedding request failed. Try again in a moment.",
                code="llm_failed",
            ) from exc

        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, list) or len(data) != len(texts):
            raise EmbeddingError(
                "Embedding response had an unexpected shape.",
                code="invalid_embed",
            )

        # OpenRouter may return items out of order — sort by index.
        ordered = sorted(
            data,
            key=lambda item: int(item.get("index", 0)) if isinstance(item, dict) else 0,
        )
        vectors: list[list[float]] = []
        for item in ordered:
            if not isinstance(item, dict):
                raise EmbeddingError(
                    "Embedding response had an unexpected shape.",
                    code="invalid_embed",
                )
            emb = item.get("embedding")
            if not isinstance(emb, list) or len(emb) != self.dimensions:
                raise EmbeddingError(
                    f"Expected {self.dimensions}-dim embeddings.",
                    code="invalid_embed",
                )
            vectors.append([float(x) for x in emb])
        return vectors


def get_embeddings_client(settings: Settings | None = None) -> EmbeddingsClient:
    return EmbeddingsClient(settings=settings)
