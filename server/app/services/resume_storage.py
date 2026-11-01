"""Local-disk resume PDF storage for onboarding parse.

MVP: one PDF per user under ``{upload_dir}/{user_id}/resume.pdf``.
Swap for Supabase Storage later without changing the onboarding router contract.

Path containment: every read/write resolves under ``root / {user_id}/`` —
filename metadata cannot traverse outside the owner directory.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.core.config import Settings, get_settings


class ResumeStorageError(ValueError):
    """Raised when a path would escape the owner upload directory."""


class ResumeStorage:
    """Read/write uploaded resume bytes on local disk."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def root(self) -> Path:
        return Path(self.settings.resume_upload_dir).expanduser().resolve()

    def user_dir(self, user_id: UUID) -> Path:
        """Absolute directory for ``user_id``; must stay under ``root``."""
        # UUID.__str__ is fixed-format — still resolve + contain for defense.
        candidate = (self.root / str(user_id)).resolve()
        self._assert_under(candidate, self.root, label="user upload directory")
        return candidate

    def resume_path(self, user_id: UUID) -> Path:
        path = (self.user_dir(user_id) / "resume.pdf").resolve()
        self._assert_under(path, self.user_dir(user_id), label="resume PDF path")
        return path

    def save(self, user_id: UUID, data: bytes, *, filename: str = "resume.pdf") -> Path:
        if not data:
            raise ValueError("Cannot store empty PDF bytes.")
        dest_dir = self.user_dir(user_id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = self.resume_path(user_id)
        dest.write_bytes(data)
        # Keep original name only as sidecar metadata for debugging.
        # Never use client filename as a path component.
        safe_name = self._sanitize_filename(filename)
        meta = (dest_dir / "filename.txt").resolve()
        self._assert_under(meta, dest_dir, label="filename metadata path")
        meta.write_text(safe_name, encoding="utf-8")
        return dest

    def load(self, user_id: UUID) -> bytes | None:
        path = self.resume_path(user_id)
        if not path.is_file():
            return None
        return path.read_bytes()

    def exists(self, user_id: UUID) -> bool:
        return self.resume_path(user_id).is_file()

    def delete(self, user_id: UUID) -> None:
        path = self.resume_path(user_id)
        if path.is_file():
            path.unlink()
        dest_dir = self.user_dir(user_id)
        meta = (dest_dir / "filename.txt").resolve()
        self._assert_under(meta, dest_dir, label="filename metadata path")
        if meta.is_file():
            meta.unlink()

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Strip path components / traversal from client-supplied names."""
        raw = (filename or "resume.pdf").strip() or "resume.pdf"
        # Drop any directory pieces the client may have sent.
        name = Path(raw).name
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            return "resume.pdf"
        return name

    @staticmethod
    def _assert_under(path: Path, parent: Path, *, label: str) -> None:
        try:
            path.relative_to(parent.resolve())
        except ValueError as exc:
            raise ResumeStorageError(
                f"{label} escapes owner upload directory."
            ) from exc


def get_resume_storage(settings: Settings | None = None) -> ResumeStorage:
    return ResumeStorage(settings=settings)
