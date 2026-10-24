"""Onboarding API: PDF upload, LLM parse, interview turns, review, complete."""

from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session

from app.core.auth import DbUser
from app.core.database import get_session
from app.schemas.onboarding import (
    InterviewItemKind,
    InterviewStateResponse,
    InterviewTranscribeResponse,
    InterviewTurnRequest,
    InterviewTurnResponse,
    OnboardingCompleteResponse,
    OnboardingParseResponse,
    OnboardingProfileUpdate,
    OnboardingResetResponse,
    OnboardingStatusResponse,
    OnboardingUploadResponse,
    ReviewGenerateResponse,
)
from app.services import onboarding as svc
from app.services.extract import ExtractError
from app.services.interview_questions import InterviewError
from app.services.profile_index import get_profile_index_service
from app.services.profile_review import ProfileReviewError
from app.services.resume_storage import ResumeStorage
from app.services.transcribe import (
    MAX_AUDIO_BYTES,
    InterviewTranscribeService,
    TranscribeError,
)

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])

SessionDep = Annotated[Session, Depends(get_session)]


def _meta(data: dict[str, Any]) -> dict[str, Any]:
    raw = data.get("_onboarding")
    return raw if isinstance(raw, dict) else {}


def _http_for_interview_error(exc: InterviewError) -> HTTPException:
    code = exc.code
    if code in {"unknown_item", "empty_interview"}:
        status_code = status.HTTP_400_BAD_REQUEST
    elif code == "openrouter_unconfigured":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_code = status.HTTP_502_BAD_GATEWAY
    return HTTPException(status_code=status_code, detail=exc.message)


def _http_for_review_error(exc: ProfileReviewError) -> HTTPException:
    code = exc.code
    if code in {"empty_review", "invalid_review"}:
        status_code = status.HTTP_502_BAD_GATEWAY
    elif code == "openrouter_unconfigured":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif code == "interview_incomplete":
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_502_BAD_GATEWAY
    return HTTPException(status_code=status_code, detail=exc.message)


def _kind(raw: object) -> InterviewItemKind:
    value = str(raw or "role")
    return cast(InterviewItemKind, value if value in ("role", "project") else "role")


def _queue_meta(
    data: dict[str, Any], queue: list[str], index: int
) -> list[dict[str, Any]]:
    """Queue chips: prefer cached LLM labels, else profile-derived labels."""
    queue_meta: list[dict[str, Any]] = []
    for i, qid in enumerate(queue):
        cached = svc.cached_interview_script(data, qid)
        if cached is not None:
            label = str(cached.get("label") or qid)
            kind = _kind(cached.get("kind"))
        else:
            label, kind_raw = svc.profile_item_label(data, qid)
            kind = _kind(kind_raw)
        state = "todo"
        if i < index:
            state = "done"
        elif i == index:
            state = "active"
        queue_meta.append({"id": qid, "label": label, "kind": kind, "state": state})
    return queue_meta


@router.get("/status", response_model=OnboardingStatusResponse)
def onboarding_status(user: DbUser, session: SessionDep) -> OnboardingStatusResponse:
    profile = svc.get_or_create_profile(session, user.id)
    meta = _meta(profile.data or {})
    return OnboardingStatusResponse(
        status=user.onboarding_status,  # type: ignore[arg-type]
        step=meta.get("step"),
        has_profile=bool(profile.data),
        resume_filename=meta.get("resume_filename"),
    )


@router.post("/upload", response_model=OnboardingUploadResponse)
async def upload_resume(
    user: DbUser,
    session: SessionDep,
    file: Annotated[UploadFile, File()],
) -> OnboardingUploadResponse:
    filename = file.filename or "resume.pdf"
    content_type = (file.content_type or "").lower()
    is_pdf = content_type == "application/pdf" or filename.lower().endswith(".pdf")
    if not is_pdf:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That file isn't a PDF. Upload a PDF resume (LinkedIn export works).",
        )

    raw = await file.read()
    if len(raw) > svc.MAX_PDF_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This file is over 10MB. Export a leaner PDF and try again.",
        )
    if len(raw) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file. Choose a PDF resume to continue.",
        )

    try:
        ResumeStorage().save(user.id, raw, filename=filename)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not store the uploaded resume. Try again.",
        ) from exc

    profile = svc.get_or_create_profile(session, user.id)
    data = dict(profile.data or {})
    data = svc.merge_onboarding_meta(
        data,
        resume_filename=filename,
        resume_size_bytes=len(raw),
        step="upload",
    )
    svc.save_profile_data(session, profile, data)
    svc.set_user_onboarding_status(session, user, "in_progress")

    return OnboardingUploadResponse(
        status="in_progress",
        filename=filename,
        size_bytes=len(raw),
    )


def _http_for_extract_error(exc: ExtractError) -> HTTPException:
    code = exc.code
    if code in {
        "missing_pdf",
        "empty_pdf",
        "empty_text",
        "empty_extract",
        "pdf_unreadable",
    }:
        status_code = status.HTTP_400_BAD_REQUEST
    elif code == "openrouter_unconfigured":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_code = status.HTTP_502_BAD_GATEWAY
    return HTTPException(status_code=status_code, detail=exc.message)


@router.post("/parse", response_model=OnboardingParseResponse)
def parse_resume(user: DbUser, session: SessionDep) -> OnboardingParseResponse:
    """PDF → markdown → OpenRouter structured Profile (stub only if explicitly allowed)."""
    profile = svc.get_or_create_profile(session, user.id)
    meta = _meta(profile.data or {})
    filename = str(meta.get("resume_filename") or "resume.pdf")
    if not meta.get("resume_filename") and not ResumeStorage().exists(user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a PDF resume before parsing.",
        )

    try:
        extracted, is_stub = svc.parse_resume_to_profile(
            user_id=user.id,
            email=user.email,
            filename=filename,
        )
    except ExtractError as exc:
        raise _http_for_extract_error(exc) from exc

    queue = svc.interview_queue_from_profile(extracted)
    public = svc.profile_public(extracted)
    data = svc.merge_onboarding_meta(
        extracted,
        resume_filename=meta.get("resume_filename") or filename,
        resume_size_bytes=meta.get("resume_size_bytes"),
        step="interview",
        interview_queue=queue,
        interview_index=0,
        question_index=0,
        coverage_hits={},
        item_transcripts={},
        parsed_snapshot=public,
    )
    svc.save_profile_data(session, profile, data)
    svc.set_user_onboarding_status(session, user, "in_progress")

    detail = (
        "STUB PARSE: demo profile (ALLOW_STUB_PARSE). Not used when OpenRouter is configured."
        if is_stub
        else "Parsed resume into a structured profile."
    )
    return OnboardingParseResponse(
        status="in_progress",
        stub=is_stub,
        detail=detail,
        profile=svc.profile_public(data),
        interview_queue=queue,
    )


@router.get("/interview", response_model=InterviewStateResponse)
def interview_state(user: DbUser, session: SessionDep) -> InterviewStateResponse:
    profile = svc.get_or_create_profile(session, user.id)
    data = dict(profile.data or {})
    meta = _meta(data)
    queue: list[str] = list(meta.get("interview_queue") or [])
    index = int(meta.get("interview_index") or 0)
    q_index = int(meta.get("question_index") or 0)
    coverage_hits_map: dict[str, Any] = dict(meta.get("coverage_hits") or {})

    if index >= len(queue):
        queue_meta = _queue_meta(data, queue, index)
        return InterviewStateResponse(
            stub=False,
            interview_complete=True,
            queue=queue_meta,
        )

    item_id = queue[index]
    had_script = svc.cached_interview_script(data, item_id) is not None
    try:
        script, data, is_stub = svc.ensure_interview_script(data, item_id)
    except InterviewError as exc:
        raise _http_for_interview_error(exc) from exc

    # Persist newly generated scripts so resume does not re-call the LLM.
    if not had_script:
        svc.save_profile_data(session, profile, data)

    questions: list[str] = [str(q) for q in list(script["questions"])]
    kind = _kind(script.get("kind"))
    label = str(script.get("label") or item_id)
    q_index = min(q_index, max(len(questions) - 1, 0))
    hits = list(coverage_hits_map.get(item_id) or [])

    return InterviewStateResponse(
        stub=is_stub,
        interview_complete=False,
        item_id=item_id,
        item_kind=kind,
        item_label=label,
        question=questions[q_index] if questions else None,
        question_index=q_index,
        question_total=len(questions),
        coverage=[str(c) for c in list(script.get("coverage") or [])],
        coverage_hits=hits,
        queue=_queue_meta(data, queue, index),
    )


def _http_for_transcribe_error(exc: TranscribeError) -> HTTPException:
    code = exc.code
    if code in {"empty_audio", "audio_too_large", "empty_transcript"}:
        status_code = status.HTTP_400_BAD_REQUEST
    elif code == "openrouter_unconfigured":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif code == "transcription_timeout":
        status_code = status.HTTP_504_GATEWAY_TIMEOUT
    else:
        status_code = status.HTTP_502_BAD_GATEWAY
    return HTTPException(status_code=status_code, detail=exc.message)


@router.post("/interview/transcribe", response_model=InterviewTranscribeResponse)
async def interview_transcribe(
    user: DbUser,
    file: Annotated[UploadFile, File()],
) -> InterviewTranscribeResponse:
    """Mic clip → Whisper transcript. Audio is not persisted."""
    _ = user  # auth gate only; no storage keyed by user
    filename = file.filename or "recording.webm"
    content_type = (file.content_type or "audio/webm").lower()
    raw = await file.read()
    if len(raw) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "That recording is too long. Keep answers to a couple of minutes, "
                "or type your answer instead."
            ),
        )
    try:
        transcript = await InterviewTranscribeService().transcribe(
            raw,
            filename=filename,
            content_type=content_type,
        )
    except TranscribeError as exc:
        raise _http_for_transcribe_error(exc) from exc

    return InterviewTranscribeResponse(
        transcript=transcript,
        detail="Transcribed with OpenRouter speech-to-text.",
    )


@router.post("/interview/turn", response_model=InterviewTurnResponse)
def interview_turn(
    body: InterviewTurnRequest,
    user: DbUser,
    session: SessionDep,
) -> InterviewTurnResponse:
    profile = svc.get_or_create_profile(session, user.id)
    data = dict(profile.data or {})
    meta = _meta(data)
    queue: list[str] = list(meta.get("interview_queue") or [])
    index = int(meta.get("interview_index") or 0)
    q_index = int(meta.get("question_index") or 0)
    coverage_hits_map: dict[str, list[str]] = {
        str(k): list(v) for k, v in dict(meta.get("coverage_hits") or {}).items()
    }

    if not queue or index >= len(queue):
        return InterviewTurnResponse(
            stub=False,
            item_id=body.item_id,
            item_kind="role",
            item_label="",
            interview_complete=True,
            item_complete=True,
            detail="All roles and projects have been interviewed.",
        )

    current_id = queue[index]
    if body.item_id != current_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected item_id {current_id}, got {body.item_id}",
        )

    try:
        script, data, is_stub = svc.ensure_interview_script(data, current_id)
    except InterviewError as exc:
        raise _http_for_interview_error(exc) from exc

    questions: list[str] = [str(q) for q in list(script["questions"])]
    coverage: list[str] = [str(c) for c in list(script.get("coverage") or [])]
    kind = _kind(script.get("kind"))
    label = str(script.get("label") or current_id)
    hits = set(coverage_hits_map.get(current_id) or [])

    transcript = body.transcript.strip()
    if not transcript and not body.force_done:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add a short answer (record or type) before continuing.",
        )

    current_question = (
        questions[q_index] if questions and q_index < len(questions) else None
    )
    if transcript:
        data = svc.store_interview_transcript(
            data,
            item_id=current_id,
            transcript=transcript,
            question=current_question,
            question_index=q_index,
        )
        if coverage:
            hits.add(coverage[min(q_index, len(coverage) - 1)])
        # Soft coverage bump when user gives multiple turns.
        if q_index >= 1 and len(coverage) > 1:
            hits.add(coverage[1])

    coverage_hits_map[current_id] = sorted(hits)
    last_q = q_index >= max(len(questions) - 1, 0)
    finish_item = body.force_done or last_q or ("that's all" in transcript.lower())

    if finish_item:
        data = svc.mark_item_interviewed(data, current_id)
        index += 1
        q_index = 0
        item_complete = True
        interview_complete = index >= len(queue)
        next_item = queue[index] if index < len(queue) else None
        step = "review" if interview_complete else "interview"

        next_question: str | None = None
        next_total = 0
        next_coverage: list[str] = []
        if next_item:
            try:
                next_script, data, is_stub = svc.ensure_interview_script(
                    data, next_item
                )
            except InterviewError as exc:
                raise _http_for_interview_error(exc) from exc
            next_qs = list(next_script.get("questions") or [])
            next_question = str(next_qs[0]) if next_qs else None
            next_total = len(next_qs)
            next_coverage = [str(c) for c in list(next_script.get("coverage") or [])]

        data = svc.merge_onboarding_meta(
            data,
            step=step,
            interview_queue=queue,
            interview_index=index,
            question_index=q_index,
            coverage_hits=coverage_hits_map,
            resume_filename=meta.get("resume_filename"),
            resume_size_bytes=meta.get("resume_size_bytes"),
        )
        svc.save_profile_data(session, profile, data)

        detail = (
            "STUB INTERVIEW: offline scripted follow-ups (ALLOW_STUB_PARSE)."
            if is_stub
            else "Interview turn saved."
        )
        return InterviewTurnResponse(
            stub=is_stub,
            item_id=current_id,
            item_kind=kind,
            item_label=label,
            question=None if interview_complete else next_question,
            question_index=0,
            question_total=next_total,
            coverage=next_coverage,
            coverage_hits=[],
            item_complete=item_complete,
            interview_complete=interview_complete,
            next_item_id=next_item,
            enriched_summary=transcript or None,
            detail=detail,
        )

    q_index += 1
    data = svc.merge_onboarding_meta(
        data,
        step="interview",
        interview_queue=queue,
        interview_index=index,
        question_index=q_index,
        coverage_hits=coverage_hits_map,
        resume_filename=meta.get("resume_filename"),
        resume_size_bytes=meta.get("resume_size_bytes"),
    )
    svc.save_profile_data(session, profile, data)

    detail = (
        "STUB INTERVIEW: offline scripted follow-ups (ALLOW_STUB_PARSE)."
        if is_stub
        else "Interview turn saved."
    )
    return InterviewTurnResponse(
        stub=is_stub,
        item_id=current_id,
        item_kind=kind,
        item_label=label,
        question=questions[q_index],
        question_index=q_index,
        question_total=len(questions),
        coverage=coverage,
        coverage_hits=sorted(hits),
        item_complete=False,
        interview_complete=False,
        next_item_id=current_id,
        enriched_summary=transcript or None,
        detail=detail,
    )


@router.post("/review/generate", response_model=ReviewGenerateResponse)
def generate_review_profile(
    user: DbUser,
    session: SessionDep,
) -> ReviewGenerateResponse:
    """Rewrite evergreen master resume from parse + interview transcripts."""
    profile = svc.get_or_create_profile(session, user.id)
    data = dict(profile.data or {})
    meta = _meta(data)
    queue = list(meta.get("interview_queue") or [])
    index = int(meta.get("interview_index") or 0)

    if queue and index < len(queue):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Finish interviewing every role and project before review.",
        )
    if not data.get("experience") and not data.get("projects"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parse a resume and finish the conversation before review.",
        )

    try:
        data, is_stub, already_ready = svc.ensure_master_rewrite(data)
    except ProfileReviewError as exc:
        raise _http_for_review_error(exc) from exc

    if not already_ready:
        svc.save_profile_data(session, profile, data)
        svc.set_user_onboarding_status(session, user, "in_progress")

    detail = (
        "STUB REVIEW: offline remade master (ALLOW_STUB_PARSE)."
        if is_stub
        else (
            "Remade master resume already ready."
            if already_ready
            else "Rewrote master resume from your resume and conversation."
        )
    )
    return ReviewGenerateResponse(
        stub=is_stub,
        already_ready=already_ready,
        detail=detail,
        profile=svc.profile_public(data),
    )


@router.get("/profile")
def get_onboarding_profile(user: DbUser, session: SessionDep) -> dict[str, Any]:
    profile = svc.get_or_create_profile(session, user.id)
    meta = _meta(profile.data or {})
    # Never expose raw interview Q&A on the public profile payload.
    safe_meta = {
        k: v
        for k, v in meta.items()
        if k not in {"item_transcripts", "parsed_snapshot"}
    }
    return {
        "status": user.onboarding_status,
        "data": svc.profile_public(profile.data or {}),
        "meta": safe_meta,
        "review_ready": svc.review_already_ready(profile.data or {}),
    }


@router.put("/profile")
def update_onboarding_profile(
    body: OnboardingProfileUpdate,
    user: DbUser,
    session: SessionDep,
) -> dict[str, Any]:
    if not isinstance(body.data, dict):
        raise HTTPException(status_code=400, detail="data must be an object")

    profile = svc.get_or_create_profile(session, user.id)
    existing = dict(profile.data or {})
    meta = _meta(existing)
    merged = dict(body.data)
    # Preserve interview meta; client review edits public fields only.
    merged["_onboarding"] = {
        **meta,
        "step": "ready",
    }
    svc.save_profile_data(session, profile, merged)
    # Review edits change remade content — refresh pgvector chunks.
    get_profile_index_service().reindex_user_best_effort(session, user.id)
    return {
        "status": user.onboarding_status,
        "data": svc.profile_public(merged),
    }


@router.post("/reset", response_model=OnboardingResetResponse)
def reset_onboarding(
    user: DbUser,
    session: SessionDep,
) -> OnboardingResetResponse:
    """Wipe master profile path and re-lock the onboarding hard gate.

    Clears: ``profile.data``, ``profile_chunk`` vectors, stored resume PDF.
    Preserves: Applications (tailored ResumeDocument history) — they are
    independent snapshots and remain useful after a re-onboard.
    """
    svc.reset_master_profile(session, user)
    try:
        ResumeStorage().delete(user.id)
    except OSError:
        # Profile/gate already reset; PDF cleanup is best-effort.
        pass
    get_profile_index_service().clear_user_chunks(session, user.id)
    return OnboardingResetResponse(status="not_started")


@router.post("/complete", response_model=OnboardingCompleteResponse)
def complete_onboarding(
    user: DbUser,
    session: SessionDep,
) -> OnboardingCompleteResponse:
    profile = svc.get_or_create_profile(session, user.id)
    data = dict(profile.data or {})
    meta = _meta(data)
    queue = list(meta.get("interview_queue") or [])
    index = int(meta.get("interview_index") or 0)

    if user.onboarding_status != "complete":
        # Enforce: all roles + projects interviewed before complete.
        if queue and index < len(queue):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Finish interviewing every role and project before continuing.",
            )
        if not data.get("experience") and not data.get("projects"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parse a resume before completing onboarding.",
            )

    data = svc.merge_onboarding_meta(
        data,
        step="ready",
        interview_queue=queue,
        interview_index=index,
        question_index=int(meta.get("question_index") or 0),
        coverage_hits=meta.get("coverage_hits") or {},
        resume_filename=meta.get("resume_filename"),
        resume_size_bytes=meta.get("resume_size_bytes"),
    )
    svc.save_profile_data(session, profile, data)
    svc.set_user_onboarding_status(session, user, "complete")
    # Re-index remade master profile for tailor RAG (best-effort).
    get_profile_index_service().reindex_user_best_effort(session, user.id)
    return OnboardingCompleteResponse(status="complete")
