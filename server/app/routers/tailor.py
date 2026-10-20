from fastapi import APIRouter

from app.core.auth import CurrentUser
from app.schemas.resume import TailorRequest, TailorResponse
from app.services.tailor import TailorService

router = APIRouter(prefix="/api/v1/tailor", tags=["tailor"])


@router.post("", response_model=TailorResponse)
def tailor_resume(body: TailorRequest, _user: CurrentUser) -> TailorResponse:
    return TailorService().tailor(body)


@router.get("/status")
def tailor_status(_user: CurrentUser) -> dict:
    return TailorService().build_llm_notes()
