"""Public waitlist capture — email only, rate-limited, no auth."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.core.database import get_session
from app.schemas.waitlist import WaitlistSignupRequest, WaitlistSignupResponse
from app.services.waitlist import WaitlistValidationError, capture_email

router = APIRouter(prefix="/api/v1/waitlist", tags=["waitlist"])

SessionDep = Annotated[Session, Depends(get_session)]

# Simple per-IP sliding window (in-process; fine for single Fly machine MVP).
_RATE_LIMIT = 10
_RATE_WINDOW_S = 60.0
_hits: dict[str, list[float]] = defaultdict(list)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _rate_limited(key: str) -> bool:
    now = time.monotonic()
    window = [t for t in _hits[key] if now - t < _RATE_WINDOW_S]
    if len(window) >= _RATE_LIMIT:
        _hits[key] = window
        return True
    window.append(now)
    _hits[key] = window
    return False


@router.post(
    "",
    response_model=WaitlistSignupResponse,
    responses={
        400: {"description": "Invalid email"},
        429: {"description": "Rate limited"},
    },
)
def signup(
    body: WaitlistSignupRequest,
    request: Request,
    session: SessionDep,
) -> WaitlistSignupResponse | JSONResponse:
    if _rate_limited(_client_key(request)):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "rate_limited",
                "message": "Too many tries. Wait a moment and try again.",
            },
        )

    try:
        result = capture_email(
            session,
            email=body.email,
            source=body.source,
            ip=_client_key(request),
            user_agent=request.headers.get("user-agent"),
        )
    except WaitlistValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_email", "message": str(exc)},
        )
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "save_failed",
                "message": "We couldn’t save that just now. Try again in a moment.",
            },
        )

    payload = WaitlistSignupResponse(
        status="ok",
        email=result.email,
        duplicate=result.duplicate,
    )
    if result.duplicate:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=payload.model_dump(),
        )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=payload.model_dump(),
    )
