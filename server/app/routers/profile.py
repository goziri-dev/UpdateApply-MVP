"""Profile CRUD backed by the persisted Profile JSONB row."""

from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.auth import DbUser
from app.core.database import get_session
from app.models.profile import Profile
from app.schemas.profile import ProfileRead, ProfileUpdate
from app.services import onboarding as onboarding_svc

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=ProfileRead)
def get_profile(user: DbUser, session: SessionDep) -> ProfileRead:
    profile = onboarding_svc.get_or_create_profile(session, user.id)
    return ProfileRead(
        id=profile.id,
        user_id=profile.user_id,
        data=onboarding_svc.profile_public(profile.data or {}),
    )


@router.put("", response_model=ProfileRead)
def put_profile(
    body: ProfileUpdate,
    user: DbUser,
    session: SessionDep,
) -> ProfileRead:
    if not isinstance(body.data, dict):
        raise HTTPException(status_code=400, detail="data must be an object")

    profile = session.exec(select(Profile).where(Profile.user_id == user.id)).first()
    if profile is None:
        profile = Profile(id=uuid4(), user_id=user.id, data={})
        session.add(profile)
        session.commit()
        session.refresh(profile)

    existing: dict[str, Any] = dict(profile.data or {})
    meta = existing.get("_onboarding")
    merged = dict(body.data)
    if isinstance(meta, dict):
        merged["_onboarding"] = meta
    onboarding_svc.save_profile_data(session, profile, merged)
    return ProfileRead(
        id=profile.id,
        user_id=profile.user_id,
        data=onboarding_svc.profile_public(merged),
    )
