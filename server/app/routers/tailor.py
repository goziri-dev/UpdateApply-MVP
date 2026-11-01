from typing import Annotated
from uuid import UUID

import sentry_sdk
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.auth import DbUser
from app.core.database import get_session
from app.core.rate_limit import LlmHeavyLimit
from app.models.job_posting import JobPosting
from app.schemas.resume import TailorRequest, TailorResponse
from app.services import credits as credits_svc
from app.services.applications import ApplicationService
from app.services.job_match import mark_opened
from app.services.tailor import TailorError, TailorService

router = APIRouter(prefix="/api/v1/tailor", tags=["tailor"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", response_model=TailorResponse)
def tailor_resume(
    body: TailorRequest,
    user: DbUser,
    session: SessionDep,
    _rl: LlmHeavyLimit,
) -> TailorResponse:
    try:
        user = credits_svc.require_credit_for_tailor(session, user)
    except credits_svc.InsufficientCreditsError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "insufficient_credits",
                "message": str(exc),
                "credit_balance": exc.balance,
                "required": exc.required,
            },
        ) from exc

    apply_url: str | None = None
    posting_uuid: UUID | None = None
    if body.posting_id:
        try:
            posting_uuid = UUID(str(body.posting_id).strip())
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid posting_id.",
            ) from exc
        posting = session.get(JobPosting, posting_uuid)
        if posting is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Posting not found.",
            )
        # Copy from stored posting only — never trust a client apply URL.
        apply_url = posting.apply_url

    try:
        with sentry_sdk.start_span(op="ai.tailor", name="tailor_resume"):
            result = TailorService().tailor(body, session=session, user_id=user.id)
    except TailorError as exc:
        code = status.HTTP_503_SERVICE_UNAVAILABLE
        if exc.code in {"empty_jd", "missing_profile"}:
            code = status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=exc.message) from exc

    # Always insert a new Applications draft — never upsert on company+role.
    company = (body.company or result.resume.meta.company or "").strip()
    role = (body.target_role or result.resume.meta.target_role or "").strip()
    row = ApplicationService().create_draft(
        session,
        user_id=user.id,
        company=company,
        target_role=role,
        job_description=body.job_description,
        resume=result.resume,
        apply_url=apply_url,
    )

    try:
        credits_svc.deduct_tailor_credit(
            session,
            user_id=user.id,
            application_id=row.id,
        )
    except credits_svc.InsufficientCreditsError as exc:
        # Race: balance spent between pre-check and deduct. Draft already saved;
        # still refuse silently completing without charge visibility.
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "insufficient_credits",
                "message": str(exc),
                "credit_balance": exc.balance,
                "required": exc.required,
                "application_id": str(row.id),
            },
        ) from exc

    if posting_uuid is not None:
        mark_opened(session, user_id=user.id, posting_id=posting_uuid)

    return result.model_copy(
        update={
            "application_id": str(row.id),
            "application_version": row.version,
            "resume": result.resume.model_copy(
                update={
                    "meta": result.resume.meta.model_copy(
                        update={
                            "company": company,
                            "target_role": role,
                            "version": row.version,
                        }
                    )
                }
            ),
        }
    )


@router.get("/status")
def tailor_status(_user: DbUser) -> dict:
    return TailorService().build_llm_notes()
