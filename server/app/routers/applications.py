"""Applications API — tailored resume history (one row per tailor success)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.auth import DbUser
from app.core.database import get_session
from app.schemas.application import (
    ApplicationDetail,
    ApplicationListResponse,
    ApplicationMarkAppliedRequest,
    ApplicationPatchRequest,
    ApplicationSummary,
)
from app.services.applications import ApplicationError, ApplicationService

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])

SessionDep = Annotated[Session, Depends(get_session)]


def _svc() -> ApplicationService:
    return ApplicationService()


@router.get("", response_model=ApplicationListResponse)
def list_applications(
    user: DbUser,
    session: SessionDep,
) -> ApplicationListResponse:
    items = _svc().list_for_user(session, user_id=user.id)
    return ApplicationListResponse(items=items)


@router.get("/{application_id}", response_model=ApplicationDetail)
def get_application(
    application_id: UUID,
    user: DbUser,
    session: SessionDep,
) -> ApplicationDetail:
    try:
        return _svc().get_detail(
            session,
            user_id=user.id,
            application_id=application_id,
        )
    except ApplicationError as exc:
        if exc.code == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=exc.message,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc


@router.post(
    "/{application_id}/mark-applied",
    response_model=ApplicationDetail,
)
def mark_applied(
    application_id: UUID,
    user: DbUser,
    session: SessionDep,
    body: ApplicationMarkAppliedRequest | None = None,
) -> ApplicationDetail:
    try:
        return _svc().mark_applied(
            session,
            user_id=user.id,
            application_id=application_id,
            applied_at=body.applied_at if body else None,
        )
    except ApplicationError as exc:
        if exc.code == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=exc.message,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc


@router.patch("/{application_id}", response_model=ApplicationDetail)
def patch_application(
    application_id: UUID,
    body: ApplicationPatchRequest,
    user: DbUser,
    session: SessionDep,
) -> ApplicationDetail:
    try:
        return _svc().patch(
            session,
            user_id=user.id,
            application_id=application_id,
            company=body.company,
            target_role=body.target_role,
            status=body.status,
            applied_at=body.applied_at,
            resume=body.resume,
        )
    except ApplicationError as exc:
        if exc.code == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=exc.message,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc


# Re-export for type checkers / tests that import summaries from the router.
__all__ = [
    "ApplicationSummary",
    "router",
]
