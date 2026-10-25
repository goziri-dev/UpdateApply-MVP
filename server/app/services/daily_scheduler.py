"""Optional in-process daily runner (enabled via ENABLE_DAILY_JOB_RUNNER).

Smallest clock around Phase 1 ingest: one asyncio loop, not a queue framework.
Prefer OS cron calling ``uv run updateapply-catalog daily`` in production.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from app.core.config import get_settings
from app.services.daily_job_run import run_daily

logger = logging.getLogger(__name__)

_task: asyncio.Task[None] | None = None


async def _loop() -> None:
    settings = get_settings()
    hour = int(settings.daily_job_runner_hour_utc)
    # Avoid firing immediately on every reload during local uvicorn --reload.
    last_run_date: str | None = None

    while True:
        try:
            now = datetime.now(UTC)
            today = now.date().isoformat()
            if now.hour == hour and last_run_date != today:
                logger.info("starting scheduled daily job run (hour=%s UTC)", hour)
                await asyncio.to_thread(run_daily, settings=settings)
                last_run_date = today
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("scheduled daily job run failed")
        await asyncio.sleep(60)


def start_daily_scheduler() -> None:
    """Start the background loop if enabled. Idempotent."""
    global _task
    settings = get_settings()
    if not settings.enable_daily_job_runner:
        return
    if _task is not None and not _task.done():
        return
    _task = asyncio.create_task(_loop(), name="updateapply-daily-job-runner")
    logger.info(
        "daily job runner enabled (hour=%s UTC)",
        settings.daily_job_runner_hour_utc,
    )


async def stop_daily_scheduler() -> None:
    global _task
    if _task is None:
        return
    _task.cancel()
    try:
        await _task
    except asyncio.CancelledError:
        pass
    _task = None
