"""Auth routes — OAuth is handled by Supabase on the Flutter client; API verifies JWTs."""

from fastapi import APIRouter

from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.schemas.auth import AuthMeResponse, AuthProviderInfo, AuthProvidersResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

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
def me(user: CurrentUser) -> AuthMeResponse:
    """Protected smoke-test: requires a valid Supabase access token."""
    return AuthMeResponse(id=user.id, email=user.email, role=user.role)
