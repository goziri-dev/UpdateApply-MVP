from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.auth import DbUser
from app.core.database import get_session
from app.schemas.resume import TailorRequest, TailorResponse
from app.services.applications import ApplicationService
from app.services.tailor import TailorError, TailorService

router = APIRouter(prefix="/api/v1/tailor", tags=["tailor"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", response_model=TailorResponse)
def tailor_resume(
    body: TailorRequest,
    user: DbUser,
    session: SessionDep,
) -> TailorResponse:
    try:
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
    )
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
