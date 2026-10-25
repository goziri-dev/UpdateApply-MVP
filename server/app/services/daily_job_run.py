"""Once-a-day catalog ingest + notify (Phase 3).

Same ingest as ``updateapply-catalog ingest`` — no user id.
Overlapping runs are blocked with a file lock.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

from sqlmodel import Session

from app.core.config import Settings, get_settings
from app.core.database import engine
from app.services.ats_ingest import AtsIngestService, IngestRunResult
from app.services.job_match import backfill_embeddings, backfill_locations
from app.services.notify_matches import NotifyRunResult, notify_all_users

logger = logging.getLogger(__name__)

_UNIT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCK_PATH = _UNIT_ROOT / "data" / "locks" / "daily_job_run.lock"


@dataclass
class DailyRunResult:
    skipped_locked: bool = False
    ingest: IngestRunResult | None = None
    locations_updated: int = 0
    embeddings_written: int = 0
    notify: NotifyRunResult | None = None
    elapsed_seconds: float = 0.0


class _FileLock:
    """Exclusive non-blocking lock so overlapping daily runs do not double-fetch."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            if os.name == "nt":
                # Windows: best-effort; solo-dev path is Unix/cron.
                return True
            import fcntl

            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.write(self._fd, f"{os.getpid()}\n".encode())
            return True
        except BlockingIOError:
            os.close(self._fd)
            self._fd = None
            return False
        except OSError:
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
            raise

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            if os.name != "nt":
                import fcntl

                fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None


def run_daily(
    *,
    settings: Settings | None = None,
    lock_path: Path | None = None,
    skip_notify: bool = False,
    skip_embed: bool = False,
) -> DailyRunResult:
    """Ingest active boards → normalize → embed → notify. Locked."""
    cfg = settings or get_settings()
    lock = _FileLock(lock_path or DEFAULT_LOCK_PATH)
    result = DailyRunResult()
    started = time.monotonic()

    if not lock.acquire():
        logger.warning("daily job run already in progress; skipping")
        result.skipped_locked = True
        return result

    try:
        with Session(engine) as session:
            with AtsIngestService(session, settings=cfg) as ingest:
                result.ingest = ingest.run()

            result.locations_updated = backfill_locations(session)
            if not skip_embed:
                result.embeddings_written = backfill_embeddings(session)

            if not skip_notify:
                result.notify = notify_all_users(session, settings=cfg)
    finally:
        lock.release()
        result.elapsed_seconds = time.monotonic() - started

    logger.info(
        "daily run done locked=%s elapsed=%.1fs ingest_ok=%s notify=%s",
        not result.skipped_locked,
        result.elapsed_seconds,
        None if result.ingest is None else result.ingest.boards_ok,
        None if result.notify is None else result.notify.notified,
    )
    return result
