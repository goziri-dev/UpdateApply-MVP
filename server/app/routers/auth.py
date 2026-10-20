"""Auth routes — OAuth is handled by Supabase on the Flutter client; API verifies JWTs."""

from fastapi import APIRouter

from app.core.auth import CurrentUser, DbUser
from app.core.config import get_settings
from app.schemas.auth import AuthMeResponse, AuthProviderInfo, AuthProvidersResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

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
def me(user: DbUser, auth: CurrentUser) -> AuthMeResponse:
    """Upsert + return the persisted app ``User`` for the Bearer JWT."""
    return AuthMeResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        oauth_provider=user.oauth_provider,
        oauth_subject=user.oauth_subject,
        role=auth.role,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
