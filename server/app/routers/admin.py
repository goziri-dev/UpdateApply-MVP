"""Favour admin: waitlist review + allowlist CRUD. Protected by X-Admin-Key."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.admin_auth import require_admin
from app.core.database import get_session
from app.schemas.admin import (
    AllowlistActionResponse,
    AllowlistAddRequest,
    AllowlistItem,
    AllowlistListResponse,
    WaitlistAdminItem,
    WaitlistAdminListResponse,
    WaitlistReviewRequest,
)
from app.services import admin_waitlist as admin_svc
from app.services import allowlist as allowlist_svc
from app.services.admin_waitlist import AdminWaitlistError
from app.services.email_notify import notify_user_approved
from app.services.waitlist import (
    WaitlistValidationError,
    normalize_email,
    validate_email,
)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)

SessionDep = Annotated[Session, Depends(get_session)]


def _waitlist_item(row: object) -> WaitlistAdminItem:
    return WaitlistAdminItem(
        id=row.id,  # type: ignore[attr-defined]
        email=row.email,  # type: ignore[attr-defined]
        name=getattr(row, "name", None),
        career_stage=getattr(row, "career_stage", None),
        job_search_challenges=getattr(row, "job_search_challenges", None),
        source=row.source,  # type: ignore[attr-defined]
        status=row.status,  # type: ignore[attr-defined]
        created_at=row.created_at,  # type: ignore[attr-defined]
        reviewed_at=row.reviewed_at,  # type: ignore[attr-defined]
        reviewed_by=row.reviewed_by,  # type: ignore[attr-defined]
        review_note=row.review_note,  # type: ignore[attr-defined]
    )


def _allowlist_item(row: object) -> AllowlistItem:
    return AllowlistItem(
        id=row.id,  # type: ignore[attr-defined]
        email=row.email,  # type: ignore[attr-defined]
        user_id=row.user_id,  # type: ignore[attr-defined]
        note=row.note,  # type: ignore[attr-defined]
        created_at=row.created_at,  # type: ignore[attr-defined]
        created_by=row.created_by,  # type: ignore[attr-defined]
        revoked_at=row.revoked_at,  # type: ignore[attr-defined]
    )


@router.get("/waitlist", response_model=WaitlistAdminListResponse)
def admin_list_waitlist(
    session: SessionDep,
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern="^(pending|approved|rejected)$"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> WaitlistAdminListResponse:
    rows = admin_svc.list_waitlist(session, status=status_filter, limit=limit)
    return WaitlistAdminListResponse(items=[_waitlist_item(r) for r in rows])


@router.post("/waitlist/{signup_id}/approve", response_model=AllowlistActionResponse)
def admin_approve_waitlist(
    signup_id: UUID,
    body: WaitlistReviewRequest,
    session: SessionDep,
) -> AllowlistActionResponse:
    try:
        row, _allow = admin_svc.approve_waitlist(
            session,
            signup_id=signup_id,
            reviewed_by=body.reviewed_by,
            note=body.note,
            notify_user=body.notify_user,
        )
    except AdminWaitlistError as exc:
        code = (
            status.HTTP_404_NOT_FOUND
            if exc.code == "not_found"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=code,
            detail={"error": exc.code, "message": exc.message},
        ) from exc
    return AllowlistActionResponse(
        status="approved",
        email=row.email,
        allowlisted=True,
    )


@router.post("/waitlist/{signup_id}/reject", response_model=AllowlistActionResponse)
def admin_reject_waitlist(
    signup_id: UUID,
    body: WaitlistReviewRequest,
    session: SessionDep,
) -> AllowlistActionResponse:
    try:
        row = admin_svc.reject_waitlist(
            session,
            signup_id=signup_id,
            reviewed_by=body.reviewed_by,
            note=body.note,
        )
    except AdminWaitlistError as exc:
        code = (
            status.HTTP_404_NOT_FOUND
            if exc.code == "not_found"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=code,
            detail={"error": exc.code, "message": exc.message},
        ) from exc
    return AllowlistActionResponse(
        status="rejected",
        email=row.email,
        allowlisted=False,
    )


@router.get("/allowlist", response_model=AllowlistListResponse)
def admin_list_allowlist(
    session: SessionDep,
    include_revoked: bool = False,
) -> AllowlistListResponse:
    rows = allowlist_svc.list_allowlist(session, include_revoked=include_revoked)
    return AllowlistListResponse(items=[_allowlist_item(r) for r in rows])


@router.post("/allowlist", response_model=AllowlistActionResponse)
def admin_add_allowlist(
    body: AllowlistAddRequest,
    session: SessionDep,
) -> AllowlistActionResponse:
    email = normalize_email(body.email)
    try:
        validate_email(email)
    except WaitlistValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_email", "message": str(exc)},
        ) from exc
    allowlist_svc.upsert_allowlist(
        session,
        email=email,
        note=body.note,
        created_by=body.created_by or "admin",
    )
    if body.notify_user:
        notify_user_approved(email=email)
    return AllowlistActionResponse(
        status="allowlisted",
        email=email,
        allowlisted=True,
    )


@router.delete("/allowlist/{email}", response_model=AllowlistActionResponse)
def admin_revoke_allowlist(
    email: str,
    session: SessionDep,
) -> AllowlistActionResponse:
    normalized = normalize_email(email)
    row = allowlist_svc.revoke_allowlist(session, normalized)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Allowlist email not found."},
        )
    return AllowlistActionResponse(
        status="revoked",
        email=normalized,
        allowlisted=False,
    )
