"""In-memory multi-turn store for resume edit sessions (MVP).

Limits (documented for operators):
- Process-local only — lost on server restart / multi-worker drift.
- TTL: ``SESSION_TTL_SECONDS`` since last access (default 1 hour).
- Cap: ``MAX_TURNS`` transcript entries per session; oldest dropped.
- Cap: ``MAX_SESSIONS`` global; oldest by last_access evicted.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

SESSION_TTL_SECONDS = 60 * 60
MAX_TURNS = 40
MAX_SESSIONS = 500


@dataclass
class EditTurn:
    role: str  # user | assistant | outcome
    content: str
    mode: str = "edit"
    outcome: str | None = None


@dataclass
class EditSession:
    session_id: str
    user_id: UUID
    turns: list[EditTurn] = field(default_factory=list)
    pending_proposal: dict[str, Any] | None = None
    created_at: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)


class EditSessionStore:
    """Thread-safe in-memory sessions keyed by session_id, scoped by user_id."""

    def __init__(
        self,
        *,
        ttl_seconds: int = SESSION_TTL_SECONDS,
        max_turns: int = MAX_TURNS,
        max_sessions: int = MAX_SESSIONS,
    ) -> None:
        self._ttl = ttl_seconds
        self._max_turns = max_turns
        self._max_sessions = max_sessions
        self._lock = threading.Lock()
        self._sessions: dict[str, EditSession] = {}

    def get_or_create(
        self,
        *,
        user_id: UUID,
        session_id: str | None,
    ) -> EditSession:
        with self._lock:
            self._purge_expired_unlocked()
            if session_id:
                existing = self._sessions.get(session_id)
                if existing is not None and existing.user_id == user_id:
                    existing.last_access = time.time()
                    return existing
            return self._create_unlocked(user_id)

    def get(self, *, user_id: UUID, session_id: str) -> EditSession | None:
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

    def append_turn(
        self,
        session: EditSession,
        turn: EditTurn,
    ) -> None:
        with self._lock:
            session.turns.append(turn)
            if len(session.turns) > self._max_turns:
                session.turns = session.turns[-self._max_turns :]
            session.last_access = time.time()

    def set_pending(
        self,
        session: EditSession,
        proposal: dict[str, Any] | None,
    ) -> None:
        with self._lock:
            session.pending_proposal = proposal
            session.last_access = time.time()

    def transcript_for_prompt(self, session: EditSession) -> list[dict[str, str]]:
        """Compact prior turns for the LLM (excludes raw resume dumps)."""
        out: list[dict[str, str]] = []
        for turn in session.turns:
            item: dict[str, str] = {
                "role": turn.role,
                "mode": turn.mode,
                "content": turn.content,
            }
            if turn.outcome:
                item["outcome"] = turn.outcome
            out.append(item)
        return out

    def _create_unlocked(self, user_id: UUID) -> EditSession:
        while len(self._sessions) >= self._max_sessions:
            oldest_id = min(
                self._sessions,
                key=lambda sid: self._sessions[sid].last_access,
            )
            del self._sessions[oldest_id]
        session = EditSession(session_id=str(uuid.uuid4()), user_id=user_id)
        self._sessions[session.session_id] = session
        return session

    def _purge_expired_unlocked(self) -> None:
        now = time.time()
        expired = [
            sid
            for sid, sess in self._sessions.items()
            if now - sess.last_access > self._ttl
        ]
        for sid in expired:
            del self._sessions[sid]


_store: EditSessionStore | None = None


def get_edit_session_store() -> EditSessionStore:
    global _store
    if _store is None:
        _store = EditSessionStore()
    return _store
