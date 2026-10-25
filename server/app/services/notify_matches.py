"""Notify users about new strong matches (Phase 3).

Channel: in-app ``match_notification`` log + optional webhook.
Does not fetch ATS boards. Does not call tailor.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlmodel import Session, col, select

from app.core.config import Settings, get_settings
from app.models.match_ledger import MatchLedger
from app.models.match_notification import MatchNotification
from app.models.match_preference import MatchPreference
from app.models.user import User
from app.services import job_match

logger = logging.getLogger(__name__)


@dataclass
class NotifyUserStats:
    user_id: UUID
    considered: int = 0
    notified: int = 0
    skipped_floor: int = 0
    skipped_already: int = 0
    skipped_cap: int = 0


@dataclass
class NotifyRunResult:
    users: int = 0
    notified: int = 0
    webhook_ok: int = 0
    webhook_failed: int = 0
    per_user: list[NotifyUserStats] = field(default_factory=list)


def _utc_day_start(d: date | None = None) -> datetime:
    day = d or datetime.now(UTC).date()
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def _notified_today_count(session: Session, user_id: UUID) -> int:
    start = _utc_day_start()
    rows = session.exec(
        select(MatchLedger).where(
            MatchLedger.user_id == user_id,
            col(MatchLedger.notified_at).is_not(None),
            col(MatchLedger.notified_at) >= start,
        )
    ).all()
    return len(list(rows))


def _already_notified_postings(session: Session, user_id: UUID) -> set[UUID]:
    rows = session.exec(
        select(MatchLedger.posting_id).where(
            MatchLedger.user_id == user_id,
            col(MatchLedger.notified_at).is_not(None),
        )
    ).all()
    return set(rows)


def _webhook_payload(notif: MatchNotification) -> dict[str, Any]:
    return {
        "type": "strong_match",
        "user_id": str(notif.user_id),
        "posting_id": str(notif.posting_id),
        "title": notif.title,
        "company": notif.company,
        "reason": notif.reason,
        "score": notif.score,
        # Vendor timestamps are approximate — do not claim "posted yesterday".
        "message": (
            f"New strong match: {notif.title} at {notif.company}. {notif.reason}"
        ),
    }


def _send_webhook(url: str, payload: dict[str, Any], *, timeout: float) -> bool:
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
        return True
    except Exception:
        logger.exception("notify webhook failed")
        return False


def notify_user(
    session: Session,
    prefs: MatchPreference,
    *,
    user_id: UUID,
    settings: Settings | None = None,
) -> NotifyUserStats:
    """Select strong unnotified matches and deliver up to the daily cap."""
    cfg = settings or get_settings()
    stats = NotifyUserStats(user_id=user_id)
    floor = float(cfg.notify_similarity_floor)
    cap = int(cfg.notify_daily_cap)

    already_today = _notified_today_count(session, user_id)
    remaining = max(0, cap - already_today)
    if remaining == 0:
        stats.skipped_cap = 1
        return stats

    # Pull a wider ranked list than the shortlist UI, then apply floor + notify rules.
    hits = job_match.shortlist_for_user(
        session,
        prefs,
        user_id=user_id,
        cap=max(cap * 3, 15),
    )
    already = _already_notified_postings(session, user_id)
    now = datetime.now(UTC)

    for hit in hits:
        stats.considered += 1
        posting = hit.posting
        if posting.id in already:
            stats.skipped_already += 1
            continue
        if float(hit.score) < floor:
            stats.skipped_floor += 1
            continue
        if stats.notified >= remaining:
            stats.skipped_cap += 1
            break

        # Stamp ledger first (unique key prevents double send).
        ledger = job_match.upsert_ledger(
            session,
            user_id=user_id,
            posting_id=posting.id,
            score=hit.score,
            reason=hit.reason,
            matched_title=hit.matched_title,
        )
        if ledger.notified_at is not None:
            stats.skipped_already += 1
            continue

        ledger.notified_at = now
        ledger.updated_at = now
        session.add(ledger)

        notif = MatchNotification(
            id=uuid4(),
            user_id=user_id,
            posting_id=posting.id,
            title=posting.title or "",
            company=posting.company_name or "",
            reason=hit.reason,
            score=hit.score,
            channel="in_app",
            created_at=now,
        )
        session.add(notif)
        session.commit()
        session.refresh(notif)

        webhook = (cfg.notify_webhook_url or "").strip()
        if webhook:
            ok = _send_webhook(
                webhook,
                _webhook_payload(notif),
                timeout=float(cfg.notify_webhook_timeout_seconds),
            )
            if not ok:
                # Log stays; webhook is best-effort.
                pass

        already.add(posting.id)
        stats.notified += 1

    return stats


def notify_all_users(
    session: Session,
    *,
    settings: Settings | None = None,
) -> NotifyRunResult:
    """Run notify for every user who has saved Job preferences. No ATS HTTP."""
    cfg = settings or get_settings()
    result = NotifyRunResult()
    prefs_rows = list(session.exec(select(MatchPreference)).all())

    for prefs in prefs_rows:
        if not (prefs.titles or []):
            continue
        user = session.get(User, prefs.user_id)
        if user is None:
            continue
        result.users += 1
        stats = notify_user(session, prefs, user_id=prefs.user_id, settings=cfg)
        result.notified += stats.notified
        result.per_user.append(stats)

    return result


def list_notifications(
    session: Session,
    user_id: UUID,
    *,
    unread_only: bool = False,
    limit: int = 50,
) -> list[MatchNotification]:
    stmt = (
        select(MatchNotification)
        .where(MatchNotification.user_id == user_id)
        .order_by(col(MatchNotification.created_at).desc())
        .limit(max(1, min(limit, 100)))
    )
    if unread_only:
        stmt = stmt.where(col(MatchNotification.read_at).is_(None))
    return list(session.exec(stmt).all())


def mark_notification_read(
    session: Session,
    user_id: UUID,
    notification_id: UUID,
) -> MatchNotification | None:
    row = session.exec(
        select(MatchNotification).where(
            MatchNotification.id == notification_id,
            MatchNotification.user_id == user_id,
        )
    ).first()
    if row is None:
        return None
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
        session.add(row)
        session.commit()
        session.refresh(row)
    return row
