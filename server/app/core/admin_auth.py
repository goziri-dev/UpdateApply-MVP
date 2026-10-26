"""Shared ADMIN_API_KEY for Favour admin endpoints (waitlist / allowlist)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


async def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
) -> None:
    if not settings.admin_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "admin_not_configured",
                "message": "Set ADMIN_API_KEY on the API to enable admin routes.",
            },
        )
    if not x_admin_key or x_admin_key.strip() != settings.admin_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "unauthorized",
                "message": "Invalid or missing X-Admin-Key.",
            },
        )


AdminAuth = Annotated[None, Depends(require_admin)]
