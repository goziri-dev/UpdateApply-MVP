"""Verify Supabase Auth JWTs for protected FastAPI routes.

Verification order (current Supabase guidance):
1. Asymmetric JWKS when the project exposes signing keys
2. HS256 with ``SUPABASE_JWT_SECRET`` (legacy shared secret)
3. Auth server ``get_user(jwt)`` as a final network check / fallback

``get_user`` verifies the Bearer JWT, upserts the app ``User`` row
(id = Supabase ``sub``), and returns the persisted SQLModel instance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Any
from uuid import UUID

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlmodel import Session
from supabase_auth.errors import AuthError

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.core.supabase import get_supabase_client
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthUser:
    id: str
    email: str | None
    role: str | None
    claims: dict[str, Any]


class AuthNotConfiguredError(RuntimeError):
    pass


@lru_cache
def _jwks_client(supabase_url: str) -> PyJWKClient:
    url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(url, cache_keys=True, lifespan=600)


def _issuer(settings: Settings) -> str:
    return f"{settings.supabase_url.rstrip('/')}/auth/v1"


def _user_from_claims(claims: dict[str, Any]) -> AuthUser:
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )
    return AuthUser(
        id=str(sub),
        email=claims.get("email"),
        role=claims.get("role"),
        claims=claims,
    )


def _provider_from_claims(claims: dict[str, Any]) -> str | None:
    """Read OAuth provider from ``app_metadata`` only (never user_metadata)."""
    app_meta = claims.get("app_metadata")
    if not isinstance(app_meta, dict):
        return None
    provider = app_meta.get("provider")
    if isinstance(provider, str) and provider.strip():
        return provider.strip()
    providers = app_meta.get("providers")
    if isinstance(providers, list) and providers:
        first = providers[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
    return None


def _verify_jwks(token: str, settings: Settings) -> AuthUser | None:
    try:
        client = _jwks_client(settings.supabase_url)
        signing_key = client.get_signing_key_from_jwt(token)
    except jwt.PyJWKClientError, jwt.InvalidTokenError, ValueError, OSError:
        return None

    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256", "EdDSA"],
            audience="authenticated",
            issuer=_issuer(settings),
        )
    except jwt.InvalidTokenError:
        return None
    return _user_from_claims(claims)


def _verify_hs256(token: str, settings: Settings) -> AuthUser | None:
    if not settings.supabase_jwt_secret:
        return None
    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            issuer=_issuer(settings),
        )
    except jwt.InvalidTokenError:
        # Some projects omit/alter issuer; retry without issuer constraint.
        try:
            claims = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except jwt.InvalidTokenError:
            return None
    return _user_from_claims(claims)


def _verify_auth_server(token: str) -> AuthUser | None:
    try:
        response = get_supabase_client().auth.get_user(token)
    except (
        AuthError,
        RuntimeError,
        ValueError,
        OSError,
        httpx.HTTPError,
        httpx.InvalidURL,
    ):
        # Network/client wiring must not 500 after local JWT paths failed.
        return None
    user = getattr(response, "user", None)
    if user is None:
        return None
    app_meta = getattr(user, "app_metadata", None) or {}
    claims: dict[str, Any] = {
        "sub": str(user.id),
        "email": getattr(user, "email", None),
        "app_metadata": app_meta if isinstance(app_meta, dict) else {},
    }
    return AuthUser(
        id=str(user.id),
        email=getattr(user, "email", None),
        role="authenticated",
        claims=claims,
    )


def verify_access_token(token: str, settings: Settings | None = None) -> AuthUser:
    settings = settings or get_settings()
    if not settings.supabase_url:
        raise AuthNotConfiguredError("SUPABASE_URL is not set")

    user = _verify_jwks(token, settings)
    if user is not None:
        return user

    user = _verify_hs256(token, settings)
    if user is not None:
        return user

    user = _verify_auth_server(token)
    if user is not None:
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def upsert_user_from_auth(session: Session, auth: AuthUser) -> User:
    """Load or create the app ``User`` keyed by Supabase ``sub``."""
    try:
        user_id = UUID(auth.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is not a valid user id",
        ) from exc

    now = datetime.now(UTC)
    provider = _provider_from_claims(auth.claims)
    existing = session.get(User, user_id)

    if existing is None:
        user = User(
            id=user_id,
            email=auth.email,
            oauth_provider=provider,
            oauth_subject=auth.id,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
    else:
        user = existing
        if auth.email is not None and user.email != auth.email:
            user.email = auth.email
        if provider is not None and user.oauth_provider != provider:
            user.oauth_provider = provider
        if user.oauth_subject != auth.id:
            user.oauth_subject = auth.id
        user.updated_at = now
        session.add(user)

    session.commit()
    session.refresh(user)
    return user


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthUser:
    # JWKS-only projects may leave JWT secret empty; still allow verify via JWKS / get_user.
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Auth is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY "
                "(plus SUPABASE_JWT_SECRET for HS256, or enable JWKS signing keys)."
            ),
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_access_token(credentials.credentials, settings)


async def get_user(
    auth: Annotated[AuthUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    """Verify JWT (via ``get_current_user``) and upsert the persisted app user."""
    return upsert_user_from_auth(session, auth)


async def get_allowlisted_user(
    auth: Annotated[AuthUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    """JWT + upsert, then require an active ``app_allowlist`` row for the email."""
    from app.services import allowlist as allowlist_svc

    if not allowlist_svc.is_email_allowlisted(session, auth.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "not_allowlisted",
                "message": (
                    "This account is not approved for the private beta yet. "
                    "Join the waitlist at https://updateapply.com — "
                    "waitlist signup does not grant access by itself."
                ),
            },
        )
    user = upsert_user_from_auth(session, auth)
    allowlist_svc.bind_user_id_if_missing(
        session,
        email=auth.email,
        user_id=user.id,
    )
    return user


CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
DbUser = Annotated[User, Depends(get_allowlisted_user)]
# JWT + upsert without allowlist (e.g. /auth/me status for blocked UX).
DbUserAny = Annotated[User, Depends(get_user)]
