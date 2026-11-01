"""Process-local sliding-window rate limits for cost-bearing LLM routes.

Interim for the solo Fly Machine (``min_machines_running = 1``). Limits are
per-process — multi-worker / multi-machine deploys need Redis (or similar)
before raising concurrency. Documented in ``.env.example``.

Keyed by authenticated user id (all LLM routes use ``DbUser`` / allowlist).
Allowlist gating still runs first via the shared ``get_allowlisted_user`` dep.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, status

from app.core.auth import get_allowlisted_user
from app.core.config import Settings, get_settings
from app.models.user import User

LlmTier = Literal["heavy", "standard"]

# Sliding windows keyed by ``f"{tier}:{user_id}"``.
_hits: dict[str, list[float]] = defaultdict(list)


def reset_rate_limit_state() -> None:
    """Clear in-memory counters (tests only)."""
    _hits.clear()


def check_rate_limit(
    key: str,
    *,
    limit: int,
    window_s: float,
    now: float | None = None,
) -> tuple[bool, float]:
    """Return ``(allowed, retry_after_seconds)``.

    When allowed, records this hit. When denied, does not record another hit.
    ``retry_after_seconds`` is 0 when allowed.
    """
    if limit <= 0:
        # 0 / negative → treat as disabled (allow). Useful in tests.
        return True, 0.0

    current = time.monotonic() if now is None else now
    window = [t for t in _hits[key] if current - t < window_s]
    if len(window) >= limit:
        _hits[key] = window
        oldest = min(window) if window else current
        retry_after = max(0.0, window_s - (current - oldest))
        return False, retry_after

    window.append(current)
    _hits[key] = window
    return True, 0.0


def _limits_for_tier(settings: Settings, tier: LlmTier) -> tuple[int, float]:
    if tier == "heavy":
        return settings.llm_rate_limit_heavy, float(
            settings.llm_rate_window_seconds_heavy
        )
    return (
        settings.llm_rate_limit_standard,
        float(settings.llm_rate_window_seconds_standard),
    )


def _rate_limit_detail(*, tier: LlmTier, retry_after: float) -> dict[str, object]:
    seconds = max(1, int(retry_after + 0.999))  # ceil without importing math
    return {
        "error": "rate_limited",
        "message": (
            "Too many AI requests. Wait a moment and try again "
            f"(retry in about {seconds}s)."
        ),
        "tier": tier,
        "retry_after_seconds": seconds,
    }


def enforce_user_rate_limit(
    *,
    user_id: str,
    tier: LlmTier,
    settings: Settings,
) -> None:
    limit, window_s = _limits_for_tier(settings, tier)
    allowed, retry_after = check_rate_limit(
        f"llm:{tier}:user:{user_id}",
        limit=limit,
        window_s=window_s,
    )
    if allowed:
        return
    detail = _rate_limit_detail(tier=tier, retry_after=retry_after)
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers={"Retry-After": str(detail["retry_after_seconds"])},
    )


def require_llm_rate_limit(tier: LlmTier) -> Callable[..., None]:
    """FastAPI dependency: allowlist user first, then per-user LLM throttle."""

    def _dependency(
        user: Annotated[User, Depends(get_allowlisted_user)],
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> None:
        enforce_user_rate_limit(
            user_id=str(user.id),
            tier=tier,
            settings=settings,
        )

    return _dependency


# Annotated deps for route signatures (after / with ``DbUser``).
LlmHeavyLimit = Annotated[None, Depends(require_llm_rate_limit("heavy"))]
LlmStandardLimit = Annotated[None, Depends(require_llm_rate_limit("standard"))]
