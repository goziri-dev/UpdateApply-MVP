"""Short-lived HMAC tokens for one-click waitlist approve/reject email links.

Uses ADMIN_API_KEY as the HMAC secret so links never embed the raw key.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from uuid import UUID

from app.core.config import Settings

DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
ACTIONS = frozenset({"approve", "reject"})


class AdminActionTokenError(ValueError):
    """Invalid or expired signed admin action token."""


def sign_waitlist_action(
    settings: Settings,
    *,
    signup_id: UUID,
    action: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: int | None = None,
) -> str:
    """Return ``{exp}.{sig}`` for a waitlist review action."""
    key = settings.admin_api_key.strip()
    if not key:
        raise AdminActionTokenError("ADMIN_API_KEY is not configured.")
    act = action.strip().lower()
    if act not in ACTIONS:
        raise AdminActionTokenError(f"Unsupported action: {action}")
    exp = int(now if now is not None else time.time()) + max(60, ttl_seconds)
    msg = f"{act}:{signup_id}:{exp}"
    sig = hmac.new(key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def verify_waitlist_action(
    settings: Settings,
    *,
    signup_id: UUID,
    action: str,
    token: str,
    now: int | None = None,
) -> None:
    """Raise ``AdminActionTokenError`` if the token is missing, expired, or forged."""
    key = settings.admin_api_key.strip()
    if not key:
        raise AdminActionTokenError("ADMIN_API_KEY is not configured.")
    act = action.strip().lower()
    if act not in ACTIONS:
        raise AdminActionTokenError(f"Unsupported action: {action}")
    raw = (token or "").strip()
    parts = raw.split(".", 1)
    if len(parts) != 2:
        raise AdminActionTokenError("Malformed token.")
    exp_s, sig = parts
    try:
        exp = int(exp_s)
    except ValueError as exc:
        raise AdminActionTokenError("Malformed token expiry.") from exc
    ts = int(now if now is not None else time.time())
    if ts > exp:
        raise AdminActionTokenError("Token expired.")
    msg = f"{act}:{signup_id}:{exp}"
    expected = hmac.new(
        key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise AdminActionTokenError("Invalid token signature.")
