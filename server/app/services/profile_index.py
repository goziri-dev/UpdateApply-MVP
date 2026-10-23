"""Chunk + embed remade master profile into pgvector; retrieve for JD tailor."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete
from sqlmodel import Session, col, select

from app.core.config import Settings, get_settings
from app.models.profile import Profile
from app.models.profile_chunk import ProfileChunk
from app.services.embeddings import (
    EmbeddingError,
    EmbeddingsClient,
    get_embeddings_client,
)
from app.services.onboarding import profile_public

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 8


@dataclass(frozen=True, slots=True)
class PreparedChunk:
    chunk_type: str
    source_item_id: str | None
    text: str
    meta: dict[str, Any]


class ProfileIndexError(Exception):
    """Raised when profile indexing / retrieve fails in a user-visible way."""

    def __init__(self, message: str, *, code: str = "index_failed") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ProfileIndexService:
    """Index remade public profile chunks; retrieve top-k for a JD query."""

    def __init__(
        self,
        settings: Settings | None = None,
        embeddings: EmbeddingsClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embeddings = embeddings or get_embeddings_client(self.settings)

    def configured(self) -> bool:
        return self.embeddings.configured()

    def reindex_profile(
        self,
        session: Session,
        *,
        user_id: UUID,
        profile: Profile,
    ) -> int:
        """Replace all chunks for ``user_id`` from remade public profile data.

        Returns the number of chunks written. Raises when OpenRouter is
        configured and embedding fails. When not configured, returns 0
        (caller may skip silently for stub/offline paths).
        """
        if not self.configured():
            logger.info("Skip profile reindex: OpenRouter not configured")
            return 0

        public = profile_public(dict(profile.data or {}))
        prepared = chunk_remade_profile(public)
        if not prepared:
            # Clear stale vectors when remade content is empty.
            session.execute(
                delete(ProfileChunk).where(col(ProfileChunk.user_id) == user_id)
            )
            session.commit()
            return 0

        try:
            vectors = self.embeddings.embed_texts([c.text for c in prepared])
        except EmbeddingError as exc:
            raise ProfileIndexError(exc.message, code=exc.code) from exc

        now = datetime.now(UTC)
        session.execute(
            delete(ProfileChunk).where(col(ProfileChunk.user_id) == user_id)
        )
        for prep, vector in zip(prepared, vectors, strict=True):
            session.add(
                ProfileChunk(
                    id=uuid4(),
                    user_id=user_id,
                    profile_id=profile.id,
                    chunk_type=prep.chunk_type,
                    source_item_id=prep.source_item_id,
                    text=prep.text,
                    embedding=vector,
                    meta=prep.meta,
                    created_at=now,
                    updated_at=now,
                )
            )
        session.commit()
        return len(prepared)

    def reindex_user_best_effort(self, session: Session, user_id: UUID) -> int:
        """Load profile and reindex; log and return 0 on failure."""
        profile = session.exec(
            select(Profile).where(Profile.user_id == user_id)
        ).first()
        if profile is None:
            return 0
        try:
            return self.reindex_profile(session, user_id=user_id, profile=profile)
        except ProfileIndexError:
            logger.exception("Profile reindex failed for user %s", user_id)
            return 0

    def retrieve_for_jd(
        self,
        session: Session,
        *,
        user_id: UUID,
        job_description: str,
        top_k: int = DEFAULT_TOP_K,
    ) -> list[ProfileChunk]:
        jd = job_description.strip()
        if not jd:
            return []
        if not self.configured():
            return []

        count = session.exec(
            select(ProfileChunk.id).where(ProfileChunk.user_id == user_id).limit(1)
        ).first()
        if count is None:
            return []

        try:
            query_vec = self.embeddings.embed_query(jd)
        except EmbeddingError as exc:
            raise ProfileIndexError(exc.message, code=exc.code) from exc

        statement = (
            select(ProfileChunk)
            .where(ProfileChunk.user_id == user_id)
            .order_by(ProfileChunk.embedding.cosine_distance(query_vec))
            .limit(max(1, top_k))
        )
        return list(session.exec(statement).all())


def chunk_remade_profile(data: dict[str, Any]) -> list[PreparedChunk]:
    """Build embeddable chunks from remade public profile JSON.

    Primary: summaries, experience/project bullets, skill groups, light role
    metadata. Does **not** include ``_onboarding`` / transcripts.
    """
    chunks: list[PreparedChunk] = []

    summary = str(data.get("summary") or "").strip()
    if summary:
        chunks.append(
            PreparedChunk(
                chunk_type="summary",
                source_item_id=None,
                text=f"Professional summary:\n{summary}",
                meta={"field": "summary"},
            )
        )

    basics = data.get("basics") if isinstance(data.get("basics"), dict) else {}
    name = str(basics.get("name") or "").strip()
    if name:
        loc = str(basics.get("location") or "").strip()
        bits = [f"Candidate: {name}"]
        if loc:
            bits.append(f"Location: {loc}")
        chunks.append(
            PreparedChunk(
                chunk_type="basics",
                source_item_id=None,
                text="\n".join(bits),
                meta={"field": "basics"},
            )
        )

    for i, raw in enumerate(data.get("experience") or [], start=1):
        if not isinstance(raw, dict):
            continue
        item_id = str(raw.get("id") or f"exp-{i}")
        company = str(raw.get("company") or "").strip()
        title = str(raw.get("title") or "").strip()
        start = str(raw.get("start") or "").strip()
        end = str(raw.get("end") or "").strip()
        role_summary = str(raw.get("summary") or "").strip()
        header = " | ".join(
            p
            for p in (
                f"{title} at {company}" if title or company else "",
                f"{start}–{end}" if start or end else "",
            )
            if p
        )
        if role_summary or header:
            body = header
            if role_summary:
                body = f"{header}\n{role_summary}" if header else role_summary
            chunks.append(
                PreparedChunk(
                    chunk_type="experience",
                    source_item_id=item_id,
                    text=f"Experience:\n{body}",
                    meta={"company": company, "title": title},
                )
            )
        for bi, bullet in enumerate(raw.get("bullets") or [], start=1):
            text = str(bullet).strip()
            if not text:
                continue
            prefix = header or "Experience"
            chunks.append(
                PreparedChunk(
                    chunk_type="experience_bullet",
                    source_item_id=item_id,
                    text=f"{prefix}\n• {text}",
                    meta={"bullet_index": bi, "company": company, "title": title},
                )
            )

    for i, raw in enumerate(data.get("projects") or [], start=1):
        if not isinstance(raw, dict):
            continue
        item_id = str(raw.get("id") or f"proj-{i}")
        title = str(raw.get("title") or "").strip()
        start = str(raw.get("start") or "").strip()
        end = str(raw.get("end") or "").strip()
        proj_summary = str(raw.get("summary") or "").strip()
        header = title or "Project"
        if start or end:
            header = f"{header} ({start}–{end})"
        if proj_summary:
            chunks.append(
                PreparedChunk(
                    chunk_type="project",
                    source_item_id=item_id,
                    text=f"Project: {header}\n{proj_summary}",
                    meta={"title": title},
                )
            )
        for bi, bullet in enumerate(raw.get("bullets") or [], start=1):
            text = str(bullet).strip()
            if not text:
                continue
            chunks.append(
                PreparedChunk(
                    chunk_type="project_bullet",
                    source_item_id=item_id,
                    text=f"Project: {header}\n• {text}",
                    meta={"bullet_index": bi, "title": title},
                )
            )

    for i, raw in enumerate(data.get("skills") or [], start=1):
        if isinstance(raw, str):
            label = raw.strip()
            if label:
                chunks.append(
                    PreparedChunk(
                        chunk_type="skills",
                        source_item_id=f"skill-{i}",
                        text=f"Skill: {label}",
                        meta={},
                    )
                )
            continue
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip() or f"Skills {i}"
        keywords = [
            str(k).strip() for k in (raw.get("keywords") or []) if str(k).strip()
        ]
        if not keywords and not name:
            continue
        body = f"Skills — {name}"
        if keywords:
            body = f"{body}: {', '.join(keywords)}"
        chunks.append(
            PreparedChunk(
                chunk_type="skills",
                source_item_id=f"skill-{i}",
                text=body,
                meta={"name": name},
            )
        )

    for i, raw in enumerate(data.get("education") or [], start=1):
        if not isinstance(raw, dict):
            continue
        school = str(raw.get("school") or "").strip()
        degree = str(raw.get("degree") or "").strip()
        end = str(raw.get("end") or "").strip()
        if not (school or degree):
            continue
        bits = [b for b in (degree, school, end) if b]
        chunks.append(
            PreparedChunk(
                chunk_type="education",
                source_item_id=f"edu-{i}",
                text=f"Education: {' — '.join(bits)}",
                meta={"school": school, "degree": degree},
            )
        )

    return chunks


def get_profile_index_service(
    settings: Settings | None = None,
) -> ProfileIndexService:
    return ProfileIndexService(settings=settings)
