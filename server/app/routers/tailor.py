from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.auth import DbUser
from app.core.database import get_session
from app.schemas.resume import TailorRequest, TailorResponse
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
        return TailorService().tailor(body, session=session, user_id=user.id)
    except TailorError as exc:
        code = status.HTTP_503_SERVICE_UNAVAILABLE
        if exc.code in {"empty_jd", "missing_profile"}:
            code = status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=exc.message) from exc


@router.get("/status")
def tailor_status(_user: DbUser) -> dict:
    return TailorService().build_llm_notes()
