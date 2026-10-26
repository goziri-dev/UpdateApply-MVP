"""Auth routes — OAuth is handled by Supabase on the Flutter client; API verifies JWTs."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.auth import CurrentUser, DbUserAny
from app.core.config import get_settings
from app.core.database import get_session
from app.schemas.auth import AuthMeResponse, AuthProviderInfo, AuthProvidersResponse
from app.services import allowlist as allowlist_svc

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

SessionDep = Annotated[Session, Depends(get_session)]

# Auth UI OAuth order: Google → GitHub → Notion (email/password via Supabase client).
_PROVIDERS = ("google", "github", "notion")


@router.get("/providers", response_model=AuthProvidersResponse)
def list_providers() -> AuthProvidersResponse:
    s = get_settings()
    configured = bool(s.supabase_url and s.supabase_anon_key)
    providers = [
        AuthProviderInfo(
            provider=name,
            authorize_url=None,
            configured=configured,
            detail=(
                "OAuth runs in the Flutter client via supabase_flutter "
                f"(signInWithOAuth → {name}). Enable the provider in "
                "Supabase Dashboard → Authentication → Providers."
            ),
        )
        for name in _PROVIDERS
    ]
    return AuthProvidersResponse(providers=providers)


@router.get("/me", response_model=AuthMeResponse)
def me(
    user: DbUserAny,
    auth: CurrentUser,
    session: SessionDep,
) -> AuthMeResponse:
    """Upsert + return app ``User``. Does not 403 when not allowlisted (UX gate)."""
    allowed = allowlist_svc.is_email_allowlisted(session, auth.email or user.email)
    if allowed:
        allowlist_svc.bind_user_id_if_missing(
            session,
            email=auth.email or user.email,
            user_id=user.id,
        )
    return AuthMeResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        oauth_provider=user.oauth_provider,
        oauth_subject=user.oauth_subject,
        onboarding_status=user.onboarding_status,
        role=auth.role,
        allowlisted=allowed,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
