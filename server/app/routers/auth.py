"""Auth stubs — Supabase Auth handles OAuth (Google, GitHub, Notion)."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.auth import AuthProviderInfo, AuthProvidersResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_PROVIDERS = ("google", "github", "notion")


@router.get("/providers", response_model=AuthProvidersResponse)
def list_providers() -> AuthProvidersResponse:
    s = get_settings()
    configured = s.supabase_configured
    providers = [
        AuthProviderInfo(
            provider=name,
            authorize_url=f"/api/v1/auth/{name}/start",
            configured=configured,
            detail=(
                "Stub — enable provider in Supabase Dashboard "
                "(Authentication → Providers), then wire Flutter "
                "supabase_flutter sign-in + API JWT verification."
            ),
        )
        for name in _PROVIDERS
    ]
    return AuthProvidersResponse(providers=providers)


@router.get("/{provider}/start")
def oauth_start(provider: str) -> dict[str, str]:
    return {
        "provider": provider,
        "status": "not_implemented",
        "detail": (
            f"OAuth for {provider} is handled by Supabase Auth on the client. "
            "Fill SUPABASE_* in server/.env and app/.env, then implement "
            "token verification on protected routes."
        ),
    }


@router.get("/{provider}/callback")
def oauth_callback(provider: str, code: str | None = None) -> dict[str, str | None]:
    return {
        "provider": provider,
        "status": "not_implemented",
        "code_received": "yes" if code else "no",
        "detail": (
            "Supabase hosts the OAuth callback. This route is unused once "
            "the Flutter client uses supabase_flutter."
        ),
    }
