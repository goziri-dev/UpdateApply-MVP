"""Waitlist capture — normalize, validate, persist. No auth / no LLM."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.waitlist_signup import WaitlistSignup
from app.schemas.waitlist import CAREER_STAGES

logger = logging.getLogger(__name__)

EMAIL_MAX = 254
NAME_MAX = 120
CHALLENGES_MAX = 1000
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@dataclass(frozen=True)
class WaitlistResult:
    email: str
    duplicate: bool


class WaitlistValidationError(ValueError):
    """Invalid waitlist signup fields."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def normalize_email(raw: str) -> str:
    return raw.strip().lower()


def normalize_name(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.strip())


def validate_email(email: str) -> None:
    if not email:
        raise WaitlistValidationError(
            "invalid_email",
            "Enter your email to join the waitlist.",
        )
    if not EMAIL_RE.match(email) or len(email) > EMAIL_MAX:
        raise WaitlistValidationError(
            "invalid_email",
            "That doesn’t look like an email we can save.",
        )


def validate_name(name: str) -> None:
    if not name:
        raise WaitlistValidationError("invalid_name", "Enter your name.")
    if len(name) > NAME_MAX:
        raise WaitlistValidationError(
            "invalid_name",
            "That name is a bit long — shorten it.",
        )


def validate_career_stage(stage: str) -> None:
    if not stage:
        raise WaitlistValidationError(
            "invalid_career_stage",
            "Choose your career stage.",
        )
    if stage not in CAREER_STAGES:
        raise WaitlistValidationError(
            "invalid_career_stage",
            "Choose a career stage from the list.",
        )


def validate_challenges(challenges: str | None) -> str | None:
    if challenges is None:
        return None
    cleaned = challenges.strip()
    if not cleaned:
        return None
    if len(cleaned) > CHALLENGES_MAX:
        raise WaitlistValidationError(
            "invalid_challenges",
            "Keep that answer under 1000 characters.",
        )
    return cleaned


def capture_email(
    session: Session,
    *,
    email: str,
    name: str,
    career_stage: str,
    job_search_challenges: str | None = None,
    source: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> WaitlistResult:
    """Insert signup. Duplicate → idempotent success (duplicate=True)."""
    normalized_email = normalize_email(email)
    normalized_name = normalize_name(name)
    stage = career_stage.strip()
    challenges = validate_challenges(job_search_challenges)

    validate_email(normalized_email)
    validate_name(normalized_name)
    validate_career_stage(stage)

    existing = session.exec(
        select(WaitlistSignup).where(WaitlistSignup.email == normalized_email)
    ).first()
    if existing is not None:
        return WaitlistResult(email=normalized_email, duplicate=True)

    src = (source or "").strip()[:64] or None
    ua = (user_agent or "").strip()[:512] or None
    ip_val = (ip or "").strip()[:64] or None

    row = WaitlistSignup(
        email=normalized_email,
        name=normalized_name,
        career_stage=stage,
        job_search_challenges=challenges,
        source=src,
        ip=ip_val,
        user_agent=ua,
        status="pending",
    )
    session.add(row)
    try:
        session.commit()
        session.refresh(row)
    except IntegrityError:
        session.rollback()
        return WaitlistResult(email=normalized_email, duplicate=True)

    # Best-effort side effects — never fail the signup path.
    try:
        from app.services.email_notify import (
            notify_favour_new_waitlist,
            notify_user_welcome,
        )

        notify_user_welcome(email=normalized_email, name=normalized_name)
        notify_favour_new_waitlist(
            email=normalized_email,
            name=normalized_name,
            career_stage=stage,
            job_search_challenges=challenges,
            source=src,
            signup_id=row.id,
            created_at=row.created_at,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        logger.warning("Waitlist notify failed for %s: %s", normalized_email, exc)

    try:
        from app.services.google_sheets_sync import append_waitlist_row

        append_waitlist_row(
            name=normalized_name,
            email=normalized_email,
            career_stage=stage,
            job_search_challenges=challenges,
            source=src,
            signup_id=str(row.id),
            created_at=row.created_at,
            status=row.status,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        logger.warning(
            "Waitlist Google Sheet sync failed for %s: %s",
            normalized_email,
            exc,
        )

    return WaitlistResult(email=normalized_email, duplicate=False)
