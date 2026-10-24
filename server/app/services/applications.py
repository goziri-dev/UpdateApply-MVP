"""Persist and query tailored application versions."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func as sa_func
from sqlmodel import Session, col, select

from app.models.application import Application
from app.schemas.application import (
    ApplicationDetail,
    ApplicationSummary,
)
from app.schemas.resume import ResumeDocument

_SNIPPET_LEN = 160
_ALLOWED_STATUS = frozenset({"draft", "applied"})


class ApplicationError(Exception):
    def __init__(self, message: str, *, code: str = "application_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def _snippet(job_description: str) -> str:
    text = " ".join(job_description.split())
    if len(text) <= _SNIPPET_LEN:
        return text
    return text[: _SNIPPET_LEN - 1].rstrip() + "…"


def _summary(row: Application) -> ApplicationSummary:
    return ApplicationSummary(
        id=row.id,
        company=row.company,
        target_role=row.target_role,
        status=row.status,
        version=row.version,
        job_snippet=_snippet(row.job_description or ""),
        applied_at=row.applied_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _detail(row: Application) -> ApplicationDetail:
    resume = ResumeDocument.model_validate(row.resume_document or {})
    base = _summary(row)
    return ApplicationDetail(
        **base.model_dump(),
        job_description=row.job_description or "",
        resume=resume,
    )


def next_version(
    session: Session,
    *,
    user_id: UUID,
    company: str,
    target_role: str,
) -> int:
    """Next version number for this user + company + role (case-insensitive)."""
    company_key = company.strip()
    role_key = target_role.strip()
    max_version = session.exec(
        select(sa_func.max(Application.version)).where(
            Application.user_id == user_id,
            sa_func.lower(Application.company) == company_key.casefold(),
            sa_func.lower(Application.target_role) == role_key.casefold(),
        )
    ).one()
    if max_version is None:
        return 1
    return int(max_version) + 1


class ApplicationService:
    def create_draft(
        self,
        session: Session,
        *,
        user_id: UUID,
        company: str,
        target_role: str,
        job_description: str,
        resume: ResumeDocument,
    ) -> Application:
        company_clean = (company or "").strip()
        role_clean = (target_role or "").strip()
        version = next_version(
            session,
            user_id=user_id,
            company=company_clean,
            target_role=role_clean,
        )
        # Keep resume meta aligned with the row.
        resume_data = resume.model_dump()
        meta = resume_data.get("meta")
        if isinstance(meta, dict):
            meta["company"] = company_clean
            meta["target_role"] = role_clean
            meta["version"] = version

        now = datetime.now(UTC)
        row = Application(
            id=uuid4(),
            user_id=user_id,
            company=company_clean,
            target_role=role_clean,
            job_description=job_description.strip(),
            resume_document=resume_data,
            status="draft",
            version=version,
            applied_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    def list_for_user(
        self,
        session: Session,
        *,
        user_id: UUID,
    ) -> list[ApplicationSummary]:
        rows = session.exec(
            select(Application)
            .where(Application.user_id == user_id)
            .order_by(col(Application.created_at).desc())
        ).all()
        return [_summary(r) for r in rows]

    def get_for_user(
        self,
        session: Session,
        *,
        user_id: UUID,
        application_id: UUID,
    ) -> Application:
        row = session.get(Application, application_id)
        if row is None or row.user_id != user_id:
            raise ApplicationError("Application not found.", code="not_found")
        return row

    def get_detail(
        self,
        session: Session,
        *,
        user_id: UUID,
        application_id: UUID,
    ) -> ApplicationDetail:
        return _detail(
            self.get_for_user(
                session,
                user_id=user_id,
                application_id=application_id,
            )
        )

    def mark_applied(
        self,
        session: Session,
        *,
        user_id: UUID,
        application_id: UUID,
        applied_at: datetime | None = None,
    ) -> ApplicationDetail:
        row = self.get_for_user(
            session,
            user_id=user_id,
            application_id=application_id,
        )
        now = datetime.now(UTC)
        when = applied_at or now
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        row.status = "applied"
        row.applied_at = when
        row.updated_at = now
        session.add(row)
        session.commit()
        session.refresh(row)
        return _detail(row)

    def patch(
        self,
        session: Session,
        *,
        user_id: UUID,
        application_id: UUID,
        company: str | None = None,
        target_role: str | None = None,
        status: str | None = None,
        applied_at: datetime | None = None,
    ) -> ApplicationDetail:
        row = self.get_for_user(
            session,
            user_id=user_id,
            application_id=application_id,
        )
        now = datetime.now(UTC)
        if company is not None:
            row.company = company.strip()
        if target_role is not None:
            row.target_role = target_role.strip()
        if status is not None:
            cleaned = status.strip().casefold()
            if cleaned not in _ALLOWED_STATUS:
                raise ApplicationError(
                    "status must be draft or applied.",
                    code="invalid_status",
                )
            row.status = cleaned
            if cleaned == "draft":
                row.applied_at = None
            elif cleaned == "applied" and row.applied_at is None:
                row.applied_at = applied_at or now
        if applied_at is not None:
            when = applied_at
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
            row.applied_at = when
            if row.status != "applied":
                row.status = "applied"
        row.updated_at = now
        session.add(row)
        session.commit()
        session.refresh(row)
        return _detail(row)


def get_application_service() -> ApplicationService:
    return ApplicationService()
