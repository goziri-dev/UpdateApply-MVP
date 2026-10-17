"""Profile stubs — persistence lands with auth + migrations applied."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.auth import CurrentUser
from app.schemas.profile import ProfileRead, ProfileUpdate

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])

# In-memory placeholder until auth + DB session are wired for a real user.
_STUB_PROFILE: dict = {
    "basics": {"name": "", "email": "", "links": []},
    "summary": "",
    "skills": [],
    "experience": [],
    "education": [],
    "projects": [],
}


@router.get("", response_model=ProfileRead)
def get_profile(user: CurrentUser) -> ProfileRead:
    return ProfileRead(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        user_id=UUID(user.id),
        data=_STUB_PROFILE,
    )


@router.put("", response_model=ProfileRead)
def put_profile(body: ProfileUpdate, user: CurrentUser) -> ProfileRead:
    if not isinstance(body.data, dict):
        raise HTTPException(status_code=400, detail="data must be an object")
    _STUB_PROFILE.clear()
    _STUB_PROFILE.update(body.data)
    return ProfileRead(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        user_id=UUID(user.id),
        data=_STUB_PROFILE,
    )
