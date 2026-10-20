"""Onboarding API: PDF upload, stub parse, interview turns, review, complete."""

from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session

from app.core.auth import DbUser
from app.core.database import get_session
from app.schemas.onboarding import (
    InterviewItemKind,
    InterviewStateResponse,
    InterviewTurnRequest,
    InterviewTurnResponse,
    OnboardingCompleteResponse,
    OnboardingParseResponse,
    OnboardingProfileUpdate,
    OnboardingStatusResponse,
    OnboardingUploadResponse,
)
from app.services import onboarding as svc

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])

SessionDep = Annotated[Session, Depends(get_session)]


def _meta(data: dict[str, Any]) -> dict[str, Any]:
    raw = data.get("_onboarding")
    return raw if isinstance(raw, dict) else {}


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

    # TODO(storage): persist PDF bytes (local disk / Supabase Storage). MVP keeps
    # only metadata so Favour can click through without object storage.
    _ = raw

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


@router.post("/parse", response_model=OnboardingParseResponse)
def parse_resume(user: DbUser, session: SessionDep) -> OnboardingParseResponse:
    """Stub structured extract. Prefer real PDF+LLM when OpenRouter is ready."""
    profile = svc.get_or_create_profile(session, user.id)
    meta = _meta(profile.data or {})
    filename = meta.get("resume_filename")
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a PDF resume before parsing.",
        )

    extracted = svc.stub_parse_profile(email=user.email)
    queue = svc.interview_queue_from_profile(extracted)
    data = svc.merge_onboarding_meta(
        extracted,
        resume_filename=filename,
        resume_size_bytes=meta.get("resume_size_bytes"),
        step="interview",
        interview_queue=queue,
        interview_index=0,
        question_index=0,
        coverage_hits={},
    )
    svc.save_profile_data(session, profile, data)
    svc.set_user_onboarding_status(session, user, "in_progress")

    return OnboardingParseResponse(
        status="in_progress",
        stub=True,
        detail=(
            "STUB PARSE: returned demo structured profile. "
            "Replace with PDF text extract + LLM when ready."
        ),
        profile=svc.profile_public(data),
        interview_queue=queue,
    )


@router.get("/interview", response_model=InterviewStateResponse)
def interview_state(user: DbUser, session: SessionDep) -> InterviewStateResponse:
    profile = svc.get_or_create_profile(session, user.id)
    data = profile.data or {}
    meta = _meta(data)
    queue: list[str] = list(meta.get("interview_queue") or [])
    index = int(meta.get("interview_index") or 0)
    q_index = int(meta.get("question_index") or 0)
    coverage_hits_map: dict[str, Any] = dict(meta.get("coverage_hits") or {})

    queue_meta: list[dict[str, Any]] = []
    for i, item_id in enumerate(queue):
        script = svc.INTERVIEW_SCRIPTS.get(item_id, {})
        state = "todo"
        if i < index:
            state = "done"
        elif i == index:
            state = "active"
        queue_meta.append(
            {
                "id": item_id,
                "label": script.get("label", item_id),
                "kind": script.get("kind", "role"),
                "state": state,
            }
        )

    if index >= len(queue):
        return InterviewStateResponse(
            stub=True,
            interview_complete=True,
            queue=queue_meta,
        )

    item_id = queue[index]
    script = svc.INTERVIEW_SCRIPTS.get(item_id)
    if script is None:
        # Fallback questions when parse ids don't match seeded scripts.
        script = {
            "label": item_id,
            "kind": "role",
            "coverage": ["Scope", "Impact"],
            "questions": [
                "Walk me through this item — what did you own and what changed because of you?",
                "Anything else I should capture before we move on?",
            ],
        }

    questions: list[str] = [str(q) for q in list(script["questions"])]
    raw_kind = str(script.get("kind") or "role")
    kind: InterviewItemKind = cast(
        InterviewItemKind,
        raw_kind if raw_kind in ("role", "project") else "role",
    )
    label = str(script.get("label") or item_id)
    q_index = min(q_index, max(len(questions) - 1, 0))
    hits = list(coverage_hits_map.get(item_id) or [])

    return InterviewStateResponse(
        stub=True,
        interview_complete=False,
        item_id=item_id,
        item_kind=kind,
        item_label=label,
        question=questions[q_index] if questions else None,
        question_index=q_index,
        question_total=len(questions),
        coverage=[str(c) for c in list(script.get("coverage") or [])],
        coverage_hits=hits,
        queue=queue_meta,
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
            stub=True,
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

    script = svc.INTERVIEW_SCRIPTS.get(
        current_id,
        {
            "label": current_id,
            "kind": "role",
            "coverage": ["Scope", "Impact"],
            "questions": [
                "Walk me through this item — what did you own?",
                "Anything else before we move on?",
            ],
        },
    )
    questions: list[str] = list(script["questions"])
    coverage: list[str] = list(script.get("coverage") or [])
    hits = set(coverage_hits_map.get(current_id) or [])

    transcript = body.transcript.strip()
    if not transcript and not body.force_done:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add a short answer (record or type) before continuing.",
        )

    if transcript:
        data = svc.apply_transcript_enrichment(
            data, item_id=current_id, transcript=transcript
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

        next_script = svc.INTERVIEW_SCRIPTS.get(next_item or "", {})
        return InterviewTurnResponse(
            stub=True,
            item_id=current_id,
            item_kind=script["kind"],
            item_label=script["label"],
            question=None
            if interview_complete
            else (next_script.get("questions") or [None])[0],
            question_index=0,
            question_total=len(next_script.get("questions") or []),
            coverage=list(next_script.get("coverage") or []),
            coverage_hits=[],
            item_complete=item_complete,
            interview_complete=interview_complete,
            next_item_id=next_item,
            enriched_summary=transcript or None,
            detail="STUB INTERVIEW: scripted follow-ups; swap for LLM later.",
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

    return InterviewTurnResponse(
        stub=True,
        item_id=current_id,
        item_kind=script["kind"],
        item_label=script["label"],
        question=questions[q_index],
        question_index=q_index,
        question_total=len(questions),
        coverage=coverage,
        coverage_hits=sorted(hits),
        item_complete=False,
        interview_complete=False,
        next_item_id=current_id,
        enriched_summary=transcript or None,
        detail="STUB INTERVIEW: scripted follow-ups; swap for LLM later.",
    )


@router.get("/profile")
def get_onboarding_profile(user: DbUser, session: SessionDep) -> dict[str, Any]:
    profile = svc.get_or_create_profile(session, user.id)
    return {
        "status": user.onboarding_status,
        "data": svc.profile_public(profile.data or {}),
        "meta": _meta(profile.data or {}),
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
    return {
        "status": user.onboarding_status,
        "data": svc.profile_public(merged),
    }


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
    return OnboardingCompleteResponse(status="complete")
