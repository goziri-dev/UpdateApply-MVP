"""Waitlist capture — normalize, validate, persist. No auth / no LLM."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.waitlist_signup import WaitlistSignup

EMAIL_MAX = 254
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@dataclass(frozen=True)
class WaitlistResult:
    email: str
    duplicate: bool


class WaitlistValidationError(ValueError):
    """Invalid email for waitlist capture."""


def normalize_email(raw: str) -> str:
    return raw.strip().lower()


def validate_email(email: str) -> None:
    if not email:
        raise WaitlistValidationError("Enter your email to join the waitlist.")
    if not EMAIL_RE.match(email) or len(email) > EMAIL_MAX:
        raise WaitlistValidationError(
            "That doesn’t look like an email we can save.",
        )


def capture_email(
    session: Session,
    *,
    email: str,
    source: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> WaitlistResult:
    """Insert normalized email. Duplicate → idempotent success (duplicate=True)."""
    normalized = normalize_email(email)
    validate_email(normalized)

    existing = session.exec(
        select(WaitlistSignup).where(WaitlistSignup.email == normalized)
    ).first()
    if existing is not None:
        return WaitlistResult(email=normalized, duplicate=True)

    src = (source or "").strip()[:64] or None
    ua = (user_agent or "").strip()[:512] or None
    ip_val = (ip or "").strip()[:64] or None

    row = WaitlistSignup(
        email=normalized,
        source=src,
        ip=ip_val,
        user_agent=ua,
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return WaitlistResult(email=normalized, duplicate=True)

    return WaitlistResult(email=normalized, duplicate=False)
