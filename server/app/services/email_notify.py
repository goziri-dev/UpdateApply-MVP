"""Transactional email via Resend (+ optional waitlist webhook).

No Resend key → log stub and return False (callers must not fail the user path).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


def _send_resend(
    settings: Settings,
    *,
    to: str,
    subject: str,
    text: str,
    html: str | None = None,
) -> bool:
    if not settings.resend_api_key.strip():
        logger.info(
            "email_notify stub (no RESEND_API_KEY): to=%s subject=%s",
            to,
            subject,
        )
        return False
    payload: dict[str, Any] = {
        "from": settings.resend_from_email,
        "to": [to],
        "subject": subject,
        "text": text,
    }
    if html:
        payload["html"] = html
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                RESEND_URL,
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key.strip()}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code >= 400:
            logger.warning(
                "Resend failed status=%s body=%s",
                resp.status_code,
                resp.text[:300],
            )
            return False
        return True
    except (httpx.HTTPError, OSError, ValueError) as exc:
        logger.warning("Resend request error: %s", exc)
        return False


def _post_webhook(url: str, payload: dict[str, Any], timeout: float) -> bool:
    if not url.strip():
        return False
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url.strip(), json=payload)
        return resp.status_code < 400
    except (httpx.HTTPError, OSError, ValueError) as exc:
        logger.warning("Waitlist webhook error: %s", exc)
        return False


def notify_favour_new_waitlist(
    *,
    email: str,
    source: str | None = None,
    settings: Settings | None = None,
) -> dict[str, bool]:
    """Email Favour (and optional webhook) when someone joins the waitlist."""
    settings = settings or get_settings()
    subject = f"[UpdateApply] New waitlist: {email}"
    text = (
        f"New waitlist signup: {email}\n"
        f"Source: {source or 'unknown'}\n\n"
        "Approve (admin API):\n"
        "  curl -X POST https://api.updateapply.com/api/v1/admin/waitlist/"
        "<id>/approve \\\n"
        "    -H 'X-Admin-Key: $ADMIN_API_KEY'\n\n"
        "Or list pending:\n"
        "  curl https://api.updateapply.com/api/v1/admin/waitlist"
        "?status=pending -H 'X-Admin-Key: $ADMIN_API_KEY'\n"
    )
    email_ok = False
    if settings.admin_notify_email.strip():
        email_ok = _send_resend(
            settings,
            to=settings.admin_notify_email.strip(),
            subject=subject,
            text=text,
        )
    elif settings.resend_api_key.strip():
        logger.warning(
            "RESEND_API_KEY set but ADMIN_NOTIFY_EMAIL empty — skip Favour email"
        )

    webhook_ok = _post_webhook(
        settings.waitlist_notify_webhook_url,
        {
            "type": "waitlist_signup",
            "email": email,
            "source": source,
        },
        timeout=10.0,
    )
    return {"email": email_ok, "webhook": webhook_ok}


def notify_user_approved(
    *,
    email: str,
    settings: Settings | None = None,
) -> bool:
    """Tell an approved user they can sign in. Optional; allowlist is the gate."""
    settings = settings or get_settings()
    app_url = settings.app_public_url.rstrip("/")
    subject = "You're in — UpdateApply private beta"
    text = (
        "You're approved for UpdateApply.\n\n"
        f"Open the app and sign in with this email: {app_url}\n\n"
        "If you signed up with Google/GitHub/Notion, use the same account.\n"
    )
    html = (
        "<p>You're approved for <strong>UpdateApply</strong>.</p>"
        f'<p><a href="{app_url}">Open the app and sign in</a> with this email.</p>'
        "<p>Use the same Google / GitHub / Notion account if that's how you sign in.</p>"
    )
    return _send_resend(
        settings,
        to=email,
        subject=subject,
        text=text,
        html=html,
    )
