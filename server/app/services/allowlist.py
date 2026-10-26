"""App allowlist — email gate after Supabase auth. Soft revoke via revoked_at."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, col, select

from app.models.app_allowlist import AppAllowlist
from app.services.waitlist import normalize_email


def is_email_allowlisted(session: Session, email: str | None) -> bool:
    if not email or not str(email).strip():
        return False
    normalized = normalize_email(email)
    row = session.exec(
        select(AppAllowlist).where(
            AppAllowlist.email == normalized,
            col(AppAllowlist.revoked_at).is_(None),
        )
    ).first()
    return row is not None


def get_active_by_email(session: Session, email: str) -> AppAllowlist | None:
    normalized = normalize_email(email)
    return session.exec(
        select(AppAllowlist).where(
            AppAllowlist.email == normalized,
            col(AppAllowlist.revoked_at).is_(None),
        )
    ).first()


def list_allowlist(
    session: Session,
    *,
    include_revoked: bool = False,
) -> list[AppAllowlist]:
    stmt = select(AppAllowlist).order_by(col(AppAllowlist.created_at).desc())
    if not include_revoked:
        stmt = stmt.where(col(AppAllowlist.revoked_at).is_(None))
    return list(session.exec(stmt).all())


def upsert_allowlist(
    session: Session,
    *,
    email: str,
    note: str | None = None,
    created_by: str | None = None,
    user_id: UUID | None = None,
) -> AppAllowlist:
    """Insert or re-activate (clear revoked_at) an allowlist row."""
    normalized = normalize_email(email)
    existing = session.exec(
        select(AppAllowlist).where(AppAllowlist.email == normalized)
    ).first()
    if existing is None:
        row = AppAllowlist(
            email=normalized,
            note=(note or "").strip()[:512] or None,
            created_by=(created_by or "").strip()[:128] or None,
            user_id=user_id,
        )
        session.add(row)
    else:
        row = existing
        row.revoked_at = None
        if note is not None:
            row.note = note.strip()[:512] or None
        if created_by is not None:
            row.created_by = created_by.strip()[:128] or None
        if user_id is not None:
            row.user_id = user_id
        session.add(row)
    session.commit()
    session.refresh(row)
    return row


def revoke_allowlist(session: Session, email: str) -> AppAllowlist | None:
    normalized = normalize_email(email)
    row = session.exec(
        select(AppAllowlist).where(AppAllowlist.email == normalized)
    ).first()
    if row is None:
        return None
    if row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def bind_user_id_if_missing(
    session: Session,
    *,
    email: str | None,
    user_id: UUID,
) -> None:
    """Attach auth user id to an active allowlist row when first seen."""
    if not email:
        return
    row = get_active_by_email(session, email)
    if row is None or row.user_id is not None:
        return
    row.user_id = user_id
    session.add(row)
    session.commit()
