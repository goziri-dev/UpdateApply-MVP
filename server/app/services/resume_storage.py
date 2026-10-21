"""Local-disk resume PDF storage for onboarding parse.

MVP: one PDF per user under ``{upload_dir}/{user_id}/resume.pdf``.
Swap for Supabase Storage later without changing the onboarding router contract.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.core.config import Settings, get_settings


class ResumeStorage:
    """Read/write uploaded resume bytes on local disk."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def root(self) -> Path:
        return Path(self.settings.resume_upload_dir).expanduser().resolve()

    def user_dir(self, user_id: UUID) -> Path:
        return self.root / str(user_id)

    def resume_path(self, user_id: UUID) -> Path:
        return self.user_dir(user_id) / "resume.pdf"

    def save(self, user_id: UUID, data: bytes, *, filename: str = "resume.pdf") -> Path:
        if not data:
            raise ValueError("Cannot store empty PDF bytes.")
        dest_dir = self.user_dir(user_id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = self.resume_path(user_id)
        dest.write_bytes(data)
        # Keep original name only as sidecar metadata for debugging.
        meta = dest_dir / "filename.txt"
        meta.write_text(
            (filename or "resume.pdf").strip() or "resume.pdf", encoding="utf-8"
        )
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
        meta = self.user_dir(user_id) / "filename.txt"
        if meta.is_file():
            meta.unlink()


def get_resume_storage(settings: Settings | None = None) -> ResumeStorage:
    return ResumeStorage(settings=settings)
