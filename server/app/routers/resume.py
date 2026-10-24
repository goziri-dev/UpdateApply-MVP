"""Resume HTML preview + PDF export + master document edit from templates."""

from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, Response
from sqlmodel import Session, select

from app.core.auth import DbUser
from app.core.database import get_session
from app.models.profile import Profile
from app.schemas.resume import (
    ResumeDeepenJournalRequest,
    ResumeDeepenJournalResponse,
    ResumeDeepenProposeRequest,
    ResumeDeepenProposeResponse,
    ResumeDeepenStartRequest,
    ResumeDeepenStateResponse,
    ResumeDeepenTurnRequest,
    ResumeDeepenTurnResponse,
    ResumeDocument,
    ResumeEditRequest,
    ResumeEditResponse,
    ResumeExportRequest,
    ResumeTemplateInfo,
)
from app.services.item_deepen import ItemDeepenError, get_item_deepen_service
from app.services.onboarding import (
    get_or_create_profile,
    profile_public,
    save_profile_data,
)
from app.services.profile_index import get_profile_index_service
from app.services.resume_document import (
    merge_profile_preserving_meta,
    profile_to_resume_document,
)
from app.services.resume_edit import ResumeEditError, get_resume_edit_service
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


@router.put("/document", response_model=ResumeDocument)
def put_document(
    body: ResumeDocument,
    user: DbUser,
    session: SessionDep,
) -> ResumeDocument:
    """Persist master ResumeDocument → profile JSON + reindex chunks.

    Preserves ``_onboarding`` meta and ``interviewed`` flags by item id.
    Prefer this over raw ``PUT /api/v1/profile`` when the client already holds
    a ResumeDocument. Does not flip onboarding status.
    """
    profile = get_or_create_profile(session, user.id)
    existing: dict[str, Any] = dict(profile.data or {})
    merged = merge_profile_preserving_meta(existing=existing, resume=body)
    save_profile_data(session, profile, merged)
    get_profile_index_service().reindex_user_best_effort(session, user.id)
    return profile_to_resume_document(profile_public(merged))


@router.post("/edit", response_model=ResumeEditResponse)
def edit_resume(body: ResumeEditRequest, user: DbUser) -> ResumeEditResponse:
    """Agentic harness turn: edit / ask (does not persist).

    Pass ``session_id`` from a prior response to continue multi-turn memory.
    Optional ``prior_outcome`` records accept/reject of the last proposal.
    """
    try:
        return get_resume_edit_service().propose(
            user_id=user.id,
            resume=body.resume,
            instruction=body.instruction,
            mode=body.mode,
            session_id=body.session_id,
            prior_outcome=body.prior_outcome,
        )
    except ResumeEditError as exc:
        bad_request = {
            "empty_instruction",
            "openrouter_missing",
            "research_unavailable",
            "empty_query",
        }
        code = (
            status.HTTP_400_BAD_REQUEST
            if exc.code in bad_request
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(status_code=code, detail=exc.message) from exc


@router.delete("/edit/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def clear_edit_session(session_id: str, user: DbUser) -> Response:
    """Drop an in-memory edit session (leave screen / explicit reset)."""
    get_resume_edit_service().clear_session(
        user_id=user.id,
        session_id=session_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _http_for_deepen_error(exc: ItemDeepenError) -> HTTPException:
    bad = {
        "bad_index",
        "missing_id",
        "empty_transcript",
        "empty_interview",
        "unknown_session",
        "unknown_item",
    }
    unconfigured = {"openrouter_unconfigured"}
    if exc.code in bad:
        code = status.HTTP_400_BAD_REQUEST
    elif exc.code in unconfigured:
        code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        code = status.HTTP_502_BAD_GATEWAY
    return HTTPException(status_code=code, detail=exc.message)


@router.post("/deepen/start", response_model=ResumeDeepenStateResponse)
def deepen_start(
    body: ResumeDeepenStartRequest,
    user: DbUser,
    session: SessionDep,
) -> ResumeDeepenStateResponse:
    """Start guided or journal deepen for one experience/project (no onboarding gate).

    Pass ``mode=guided`` (default) for novel consultant Qs, or ``mode=journal``
    for a freeform dump session. Prior questions for novelty come from profile
    ``_deepen`` + onboarding transcripts for this item id.
    """
    try:
        return get_item_deepen_service().start(user_id=user.id, body=body, db=session)
    except ItemDeepenError as exc:
        raise _http_for_deepen_error(exc) from exc


@router.post("/deepen/journal", response_model=ResumeDeepenJournalResponse)
def deepen_journal(
    body: ResumeDeepenJournalRequest,
    user: DbUser,
    session: SessionDep,
) -> ResumeDeepenJournalResponse:
    """Freeform journal dump → optional one clarify, else enriched proposal.

    Does not persist the resume; Accept in the client then Save as usual.
    Records asked/clarify themes under profile ``_deepen`` for novelty.
    """
    try:
        return get_item_deepen_service().journal(user_id=user.id, body=body, db=session)
    except ItemDeepenError as exc:
        raise _http_for_deepen_error(exc) from exc


@router.get("/deepen/{session_id}", response_model=ResumeDeepenStateResponse)
def deepen_state(session_id: str, user: DbUser) -> ResumeDeepenStateResponse:
    try:
        return get_item_deepen_service().state(user_id=user.id, session_id=session_id)
    except ItemDeepenError as exc:
        raise _http_for_deepen_error(exc) from exc


@router.post("/deepen/turn", response_model=ResumeDeepenTurnResponse)
def deepen_turn(
    body: ResumeDeepenTurnRequest,
    user: DbUser,
    session: SessionDep,
) -> ResumeDeepenTurnResponse:
    try:
        return get_item_deepen_service().turn(user_id=user.id, body=body, db=session)
    except ItemDeepenError as exc:
        raise _http_for_deepen_error(exc) from exc


@router.post("/deepen/propose", response_model=ResumeDeepenProposeResponse)
def deepen_propose(
    body: ResumeDeepenProposeRequest,
    user: DbUser,
    session: SessionDep,
) -> ResumeDeepenProposeResponse:
    """Item-level rewrite from deepen transcripts — does not persist the resume.

    Records asked questions under profile ``_deepen`` so later deepens stay novel.
    """
    try:
        return get_item_deepen_service().propose(user_id=user.id, body=body, db=session)
    except ItemDeepenError as exc:
        raise _http_for_deepen_error(exc) from exc


@router.delete("/deepen/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def deepen_clear(session_id: str, user: DbUser) -> Response:
    get_item_deepen_service().clear(user_id=user.id, session_id=session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
