"""Verify Supabase Auth JWTs for protected FastAPI routes.

Verification order (current Supabase guidance):
1. Asymmetric JWKS when the project exposes signing keys
2. HS256 with ``SUPABASE_JWT_SECRET`` (legacy shared secret)
3. Auth server ``get_user(jwt)`` as a final network check / fallback
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from supabase_auth.errors import AuthError

from app.core.config import Settings, get_settings
from app.core.supabase import get_supabase_client

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
    except AuthError, RuntimeError, ValueError, OSError:
        return None
    user = getattr(response, "user", None)
    if user is None:
        return None
    return AuthUser(
        id=str(user.id),
        email=getattr(user, "email", None),
        role="authenticated",
        claims={"sub": str(user.id), "email": getattr(user, "email", None)},
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


CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
