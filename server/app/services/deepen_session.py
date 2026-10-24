"""In-memory sessions for post-onboarding item deepen (voice enrichment).

Limits mirror edit sessions: process-local, TTL, capped count. Does not touch
onboarding gate / status — deepen is enrichment on a client-held document.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

SESSION_TTL_SECONDS = 60 * 60
MAX_SESSIONS = 500


@dataclass
class DeepenSession:
    session_id: str
    user_id: UUID
    section: Literal["experience", "projects"]
    index: int
    item_id: str
    kind: Literal["role", "project"]
    resume: dict[str, Any]
    script: dict[str, Any]
    mode: Literal["guided", "journal"] = "guided"
    question_index: int = 0
    coverage_hits: list[str] = field(default_factory=list)
    transcripts: list[dict[str, Any]] = field(default_factory=list)
    item_complete: bool = False
    clarify_pending: bool = False
    proposed_item: dict[str, Any] | None = None
    history_recorded: bool = False
    stub: bool = False
    created_at: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)


class DeepenSessionStore:
    """Thread-safe in-memory deepen sessions keyed by session_id."""

    def __init__(
        self,
        *,
        ttl_seconds: int = SESSION_TTL_SECONDS,
        max_sessions: int = MAX_SESSIONS,
    ) -> None:
        self._ttl = ttl_seconds
        self._max_sessions = max_sessions
        self._lock = threading.Lock()
        self._sessions: dict[str, DeepenSession] = {}

    def create(self, session: DeepenSession) -> DeepenSession:
        with self._lock:
            self._purge_expired_unlocked()
            while len(self._sessions) >= self._max_sessions:
                oldest_id = min(
                    self._sessions,
                    key=lambda sid: self._sessions[sid].last_access,
                )
                del self._sessions[oldest_id]
            self._sessions[session.session_id] = session
            return session

    def get(self, *, user_id: UUID, session_id: str) -> DeepenSession | None:
        with self._lock:
            self._purge_expired_unlocked()
            session = self._sessions.get(session_id)
            if session is None or session.user_id != user_id:
                return None
            session.last_access = time.time()
            return session

    def delete(self, *, user_id: UUID, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.user_id != user_id:
                return False
            del self._sessions[session_id]
            return True

    def touch(self, session: DeepenSession) -> None:
        with self._lock:
            session.last_access = time.time()

    def _purge_expired_unlocked(self) -> None:
        now = time.time()
        expired = [
            sid
            for sid, sess in self._sessions.items()
            if now - sess.last_access > self._ttl
        ]
        for sid in expired:
            del self._sessions[sid]


_store: DeepenSessionStore | None = None


def get_deepen_session_store() -> DeepenSessionStore:
    global _store
    if _store is None:
        _store = DeepenSessionStore()
    return _store


def new_session_id() -> str:
    return str(uuid.uuid4())
