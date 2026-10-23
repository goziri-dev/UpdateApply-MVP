"""Resume HTML preview + PDF export from versioned templates."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, Response
from sqlmodel import Session, select

from app.core.auth import DbUser
from app.core.database import get_session
from app.models.profile import Profile
from app.schemas.resume import (
    ResumeDocument,
    ResumeExportRequest,
    ResumeTemplateInfo,
)
from app.services.onboarding import get_or_create_profile, profile_public
from app.services.resume_document import profile_to_resume_document
from app.services.resume_export import (
    ResumeExportError,
    download_filename,
    resume_to_pdf_bytes,
)
from app.services.resume_render import (
    ResumeTemplateError,
    list_templates,
    render_resume_html,
)

router = APIRouter(prefix="/api/v1/resume", tags=["resume"])

SessionDep = Annotated[Session, Depends(get_session)]


def _master_resume(session: Session, user_id: UUID) -> ResumeDocument:
    """Remade master profile rendered as ResumeDocument (reveal + dashboard)."""
    profile = get_or_create_profile(session, user_id)
    return profile_to_resume_document(profile_public(dict(profile.data or {})))


def _resolve_resume(
    body_resume: ResumeDocument | None,
    session: Session,
    user_id: UUID,
) -> ResumeDocument:
    if body_resume is not None:
        return body_resume
    profile = session.exec(select(Profile).where(Profile.user_id == user_id)).first()
    if profile is None or not (profile.data or {}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No remade master profile yet. Finish onboarding first.",
        )
    return profile_to_resume_document(profile_public(dict(profile.data or {})))


@router.get("/templates", response_model=list[ResumeTemplateInfo])
def get_templates(_user: DbUser) -> list[ResumeTemplateInfo]:
    return list_templates()


@router.get("/document", response_model=ResumeDocument)
def get_document(user: DbUser, session: SessionDep) -> ResumeDocument:
    """Master profile as ResumeDocument — same JSON the HTML template fills."""
    return _master_resume(session, user.id)


@router.get("/html", response_class=HTMLResponse)
def get_html(
    user: DbUser,
    session: SessionDep,
    template_id: Annotated[str, Query()] = "classic",
) -> HTMLResponse:
    """Server-rendered HTML for iframe preview (same source as PDF)."""
    resume = _master_resume(session, user.id)
    try:
        html = render_resume_html(resume, template_id=template_id)
    except ResumeTemplateError as exc:
        code = (
            status.HTTP_404_NOT_FOUND
            if exc.code == "unknown_template"
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(status_code=code, detail=exc.message) from exc
    return HTMLResponse(content=html)


@router.post("/html", response_class=HTMLResponse)
def post_html(
    body: ResumeExportRequest,
    user: DbUser,
    session: SessionDep,
) -> HTMLResponse:
    """Render HTML for an explicit ResumeDocument (e.g. tailored result)."""
    resume = _resolve_resume(body.resume, session, user.id)
    try:
        html = render_resume_html(resume, template_id=body.template_id)
    except ResumeTemplateError as exc:
        code = (
            status.HTTP_404_NOT_FOUND
            if exc.code == "unknown_template"
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(status_code=code, detail=exc.message) from exc
    return HTMLResponse(content=html)


@router.post("/export")
def export_pdf(
    body: ResumeExportRequest,
    user: DbUser,
    session: SessionDep,
) -> Response:
    """Canonical download: WeasyPrint PDF from the same HTML template + JSON."""
    resume = _resolve_resume(body.resume, session, user.id)
    try:
        pdf = resume_to_pdf_bytes(resume, template_id=body.template_id)
    except ResumeTemplateError as exc:
        code = (
            status.HTTP_404_NOT_FOUND
            if exc.code == "unknown_template"
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(status_code=code, detail=exc.message) from exc
    except ResumeExportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
        ) from exc

    filename = download_filename(resume)
    # RFC 5987 for non-ASCII names; ASCII fallback for older agents.
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "resume.pdf"
    disposition = (
        f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": disposition},
    )
