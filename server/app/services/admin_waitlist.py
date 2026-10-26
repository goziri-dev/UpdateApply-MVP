"""Admin waitlist review → allowlist. Does not create auth sessions."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, col, select

from app.models.waitlist_signup import WaitlistSignup
from app.services import allowlist as allowlist_svc
from app.services.email_notify import notify_user_approved


class AdminWaitlistError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def list_waitlist(
    session: Session,
    *,
    status: str | None = None,
    limit: int = 100,
) -> list[WaitlistSignup]:
    lim = max(1, min(limit, 500))
    stmt = select(WaitlistSignup).order_by(col(WaitlistSignup.created_at).desc())
    if status:
        stmt = stmt.where(WaitlistSignup.status == status)
    stmt = stmt.limit(lim)
    return list(session.exec(stmt).all())


def approve_waitlist(
    session: Session,
    *,
    signup_id: UUID,
    reviewed_by: str | None = None,
    note: str | None = None,
    notify_user: bool = True,
) -> tuple[WaitlistSignup, object]:
    row = session.get(WaitlistSignup, signup_id)
    if row is None:
        raise AdminWaitlistError("not_found", "Waitlist signup not found.")

    now = datetime.now(UTC)
    row.status = "approved"
    row.reviewed_at = now
    row.reviewed_by = (reviewed_by or "admin").strip()[:128] or "admin"
    row.review_note = (note or "").strip()[:512] or None
    session.add(row)
    session.commit()
    session.refresh(row)

    allow_row = allowlist_svc.upsert_allowlist(
        session,
        email=row.email,
        note=note or f"Approved from waitlist {row.id}",
        created_by=row.reviewed_by,
    )

    if notify_user:
        notify_user_approved(email=row.email)

    return row, allow_row


def reject_waitlist(
    session: Session,
    *,
    signup_id: UUID,
    reviewed_by: str | None = None,
    note: str | None = None,
) -> WaitlistSignup:
    """Mark waitlist rejected and revoke any active allowlist row for that email.

    Reject does not delete the waitlist row (re-join stays a duplicate) and does
    not ban Supabase Auth — the product gate is ``app_allowlist`` after sign-in.
    """
    row = session.get(WaitlistSignup, signup_id)
    if row is None:
        raise AdminWaitlistError("not_found", "Waitlist signup not found.")

    row.status = "rejected"
    row.reviewed_at = datetime.now(UTC)
    row.reviewed_by = (reviewed_by or "admin").strip()[:128] or "admin"
    row.review_note = (note or "").strip()[:512] or None
    session.add(row)
    session.commit()
    session.refresh(row)

    # Symmetric with approve → upsert allowlist: reject removes app access.
    allowlist_svc.revoke_allowlist(session, row.email)
    return row
