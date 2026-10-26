"""Transactional email via Resend (+ optional waitlist webhook).

No Resend key → log stub and return False (callers must not fail the user path).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from html import escape
from typing import Any
from uuid import UUID

import httpx

from app.core.config import Settings, get_settings
from app.services.admin_action_token import (
    AdminActionTokenError,
    sign_waitlist_action,
)

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


def _format_submitted_at(created_at: datetime | None) -> str:
    if created_at is None:
        return "unknown"
    # Always render UTC so Favour’s inbox isn’t tied to the API host TZ.
    if created_at.tzinfo is None:
        dt = created_at.replace(tzinfo=UTC)
    else:
        dt = created_at.astimezone(UTC)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _api_base(settings: Settings) -> str:
    return settings.api_public_url.rstrip("/")


def build_waitlist_action_urls(
    settings: Settings,
    *,
    signup_id: UUID,
) -> tuple[str | None, str | None]:
    """Return (approve_url, reject_url) or (None, None) if signing is unavailable."""
    if not settings.admin_configured:
        return None, None
    try:
        approve_t = sign_waitlist_action(
            settings, signup_id=signup_id, action="approve"
        )
        reject_t = sign_waitlist_action(settings, signup_id=signup_id, action="reject")
    except AdminActionTokenError:
        return None, None
    base = f"{_api_base(settings)}/api/v1/admin/waitlist/{signup_id}"
    return (
        f"{base}/approve?t={approve_t}",
        f"{base}/reject?t={reject_t}",
    )


def build_favour_waitlist_email(
    *,
    email: str,
    source: str | None,
    signup_id: UUID | None,
    created_at: datetime | None,
    settings: Settings,
) -> tuple[str, str, str | None]:
    """Return (subject, text, html) for Favour’s new-signup notify."""
    subject = f"[UpdateApply] New waitlist signup: {email}"
    src = source or "unknown"
    sid = str(signup_id) if signup_id is not None else "unknown"
    submitted = _format_submitted_at(created_at)

    approve_url: str | None = None
    reject_url: str | None = None
    if signup_id is not None:
        approve_url, reject_url = build_waitlist_action_urls(
            settings, signup_id=signup_id
        )

    text_lines = [
        "New waitlist signup",
        "",
        f"Email: {email}",
        f"Source: {src}",
        f"Waitlist id: {sid}",
        f"Submitted at: {submitted}",
        "",
    ]
    if approve_url and reject_url:
        text_lines.extend(
            [
                "Approve (one-click, expires in 7 days):",
                f"  {approve_url}",
                "",
                "Reject (one-click, expires in 7 days):",
                f"  {reject_url}",
                "",
            ]
        )
    else:
        text_lines.append(
            "Signed Approve/Reject links unavailable "
            "(ADMIN_API_KEY or signup id missing).",
        )
        text_lines.append("")

    text = "\n".join(text_lines)

    e_email = escape(email)
    e_src = escape(src)
    e_sid = escape(sid)
    e_submitted = escape(submitted)
    if approve_url and reject_url:
        actions_html = (
            "<p style='margin:24px 0'>"
            f"<a href='{escape(approve_url)}' "
            "style='display:inline-block;padding:10px 18px;margin-right:12px;"
            "background:#0f766e;color:#fff;text-decoration:none;"
            "border-radius:6px;font-weight:600'>Approve</a>"
            f"<a href='{escape(reject_url)}' "
            "style='display:inline-block;padding:10px 18px;"
            "background:#b91c1c;color:#fff;text-decoration:none;"
            "border-radius:6px;font-weight:600'>Reject</a>"
            "</p>"
            "<p style='color:#666;font-size:13px'>"
            "Links expire in 7 days and do not include your admin API key."
            "</p>"
        )
    else:
        actions_html = (
            "<p style='color:#666'>Signed Approve/Reject links unavailable "
            "(ADMIN_API_KEY or signup id missing).</p>"
        )

    html = (
        "<div style='font-family:ui-sans-serif,system-ui,sans-serif;"
        "line-height:1.5;color:#111'>"
        "<h2 style='font-size:18px;margin:0 0 12px'>New waitlist signup</h2>"
        "<table style='border-collapse:collapse;font-size:14px'>"
        f"<tr><td style='padding:4px 12px 4px 0;color:#555'>Email</td>"
        f"<td><strong>{e_email}</strong></td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;color:#555'>Source</td>"
        f"<td>{e_src}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;color:#555'>Waitlist id</td>"
        f"<td style='font-family:ui-monospace,monospace;font-size:12px'>"
        f"{e_sid}</td></tr>"
        f"<tr><td style='padding:4px 12px 4px 0;color:#555'>Submitted at</td>"
        f"<td>{e_submitted}</td></tr>"
        "</table>"
        f"{actions_html}"
        "</div>"
    )
    return subject, text, html


def notify_favour_new_waitlist(
    *,
    email: str,
    source: str | None = None,
    signup_id: UUID | None = None,
    created_at: datetime | None = None,
    settings: Settings | None = None,
) -> dict[str, bool]:
    """Email Favour (and optional webhook) when someone joins the waitlist."""
    settings = settings or get_settings()
    subject, text, html = build_favour_waitlist_email(
        email=email,
        source=source,
        signup_id=signup_id,
        created_at=created_at,
        settings=settings,
    )
    email_ok = False
    if settings.admin_notify_email.strip():
        email_ok = _send_resend(
            settings,
            to=settings.admin_notify_email.strip(),
            subject=subject,
            text=text,
            html=html,
        )
    elif settings.resend_api_key.strip():
        logger.warning(
            "RESEND_API_KEY set but ADMIN_NOTIFY_EMAIL empty — skip Favour email"
        )

    webhook_payload: dict[str, Any] = {
        "type": "waitlist_signup",
        "email": email,
        "source": source,
    }
    if signup_id is not None:
        webhook_payload["signup_id"] = str(signup_id)
    if created_at is not None:
        webhook_payload["created_at"] = created_at.isoformat()

    webhook_ok = _post_webhook(
        settings.waitlist_notify_webhook_url,
        webhook_payload,
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
