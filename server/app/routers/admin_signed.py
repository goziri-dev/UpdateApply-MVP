"""One-click waitlist approve/reject via signed email links (no X-Admin-Key)."""

from __future__ import annotations

from html import escape
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.models.waitlist_signup import WaitlistSignup
from app.services import admin_waitlist as admin_svc
from app.services.admin_action_token import (
    AdminActionTokenError,
    verify_waitlist_action,
)
from app.services.admin_waitlist import AdminWaitlistError

router = APIRouter(prefix="/api/v1/admin/waitlist", tags=["admin-signed"])

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
Action = Literal["approve", "reject"]


def _page(title: str, body: str, *, ok: bool) -> HTMLResponse:
    color = "#0f766e" if ok else "#b91c1c"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{escape(title)} — UpdateApply</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem;
           line-height: 1.5; color: #111; }}
    h1 {{ font-size: 1.25rem; color: {color}; }}
    p {{ color: #333; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <p>{body}</p>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200 if ok else 400)


def _run_signed_action(
    *,
    signup_id: UUID,
    action: Action,
    token: str,
    session: Session,
    settings: Settings,
) -> HTMLResponse:
    try:
        verify_waitlist_action(
            settings,
            signup_id=signup_id,
            action=action,
            token=token,
        )
    except AdminActionTokenError as exc:
        return _page("Link invalid", escape(str(exc)), ok=False)

    row = session.get(WaitlistSignup, signup_id)
    if row is None:
        return _page("Not found", "That waitlist signup no longer exists.", ok=False)

    email = escape(row.email)

    if action == "approve" and row.status == "approved":
        return _page(
            "Already approved",
            f"{email} is already approved and allowlisted.",
            ok=True,
        )
    if action == "reject" and row.status == "rejected":
        return _page(
            "Already rejected",
            f"{email} was already rejected.",
            ok=True,
        )

    try:
        if action == "approve":
            admin_svc.approve_waitlist(
                session,
                signup_id=signup_id,
                reviewed_by="email-link",
                note="Approved via signed email link",
                notify_user=True,
            )
            return _page(
                "Approved",
                (
                    f"{email} is approved and allowlisted. "
                    "They’ll get a “you’re in” email if Resend is configured."
                ),
                ok=True,
            )
        admin_svc.reject_waitlist(
            session,
            signup_id=signup_id,
            reviewed_by="email-link",
            note="Rejected via signed email link",
        )
        return _page(
            "Rejected",
            (
                f"{email} was rejected. Any allowlist entry for this email "
                "was revoked — they can still sign in with Supabase, but the "
                "app stays blocked until you Approve again."
            ),
            ok=True,
        )
    except AdminWaitlistError as exc:
        return _page("Could not update", escape(exc.message), ok=False)


@router.get("/{signup_id}/approve", response_class=HTMLResponse)
def signed_approve_waitlist(
    signup_id: UUID,
    session: SessionDep,
    settings: SettingsDep,
    t: Annotated[str, Query(description="Signed action token")],
) -> HTMLResponse:
    """Gmail-friendly one-click approve. Token is HMAC over action+id+expiry."""
    return _run_signed_action(
        signup_id=signup_id,
        action="approve",
        token=t,
        session=session,
        settings=settings,
    )


@router.get("/{signup_id}/reject", response_class=HTMLResponse)
def signed_reject_waitlist(
    signup_id: UUID,
    session: SessionDep,
    settings: SettingsDep,
    t: Annotated[str, Query(description="Signed action token")],
) -> HTMLResponse:
    """Gmail-friendly one-click reject. Token is HMAC over action+id+expiry."""
    return _run_signed_action(
        signup_id=signup_id,
        action="reject",
        token=t,
        session=session,
        settings=settings,
    )
