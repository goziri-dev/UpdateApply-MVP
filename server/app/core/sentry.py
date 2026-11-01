"""Sentry init for the FastAPI app (no-op when SENTRY_DSN is empty)."""

from __future__ import annotations

from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.core.config import Settings


def init_sentry(settings: Settings) -> bool:
    """Initialize Sentry when ``SENTRY_DSN`` is set. Returns whether init ran."""
    dsn = settings.sentry_dsn.strip()
    if not dsn:
        return False

    sample_rate = settings.sentry_traces_sample_rate

    def traces_sampler(sampling_context: dict[str, Any]) -> float:
        """Respect parent sampling; drop /health; otherwise use env rate."""
        parent = sampling_context.get("parent_sampled")
        if parent is not None:
            return float(parent)

        asgi_scope = sampling_context.get("asgi_scope") or {}
        path = str(asgi_scope.get("path") or "")
        if path.rstrip("/") == "/health":
            return 0.0

        return sample_rate

    # Keep PII off by default (no send_default_pii / user_info collection).
    # Auth headers, cookies, and IPs stay scrubbed unless Favour opts in later.
    sentry_sdk.init(
        dsn=dsn,
        environment=settings.sentry_environment.strip() or None,
        release=settings.sentry_release.strip() or None,
        traces_sampler=traces_sampler,
        profile_session_sample_rate=settings.sentry_profile_session_sample_rate,
        profile_lifecycle="trace",
        send_default_pii=False,
        integrations=[
            # "url" → low-cardinality path templates in Performance (e.g. /api/v1/tailor).
            StarletteIntegration(transaction_style="url"),
            FastApiIntegration(transaction_style="url"),
        ],
    )
    return True
