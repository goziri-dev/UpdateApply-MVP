"""Profile stubs — persistence lands with auth + migrations applied."""

from fastapi import APIRouter, HTTPException

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
def get_profile() -> ProfileRead:
    from uuid import UUID

    return ProfileRead(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        user_id=UUID("00000000-0000-0000-0000-000000000002"),
        data=_STUB_PROFILE,
    )


@router.put("", response_model=ProfileRead)
def put_profile(body: ProfileUpdate) -> ProfileRead:
    from uuid import UUID

    if not isinstance(body.data, dict):
        raise HTTPException(status_code=400, detail="data must be an object")
    _STUB_PROFILE.clear()
    _STUB_PROFILE.update(body.data)
    return ProfileRead(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        user_id=UUID("00000000-0000-0000-0000-000000000002"),
        data=_STUB_PROFILE,
    )
