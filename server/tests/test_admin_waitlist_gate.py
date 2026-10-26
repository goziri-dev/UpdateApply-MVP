"""Waitlist approve/reject ↔ allowlist gate semantics (mocked session)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services import admin_waitlist as admin_svc
from app.services.admin_waitlist import AdminWaitlistError
from app.services.allowlist import is_email_allowlisted


def test_is_email_allowlisted_false_for_empty() -> None:
    session = MagicMock()
    assert is_email_allowlisted(session, None) is False
    assert is_email_allowlisted(session, "  ") is False
    session.exec.assert_not_called()


def test_approve_upserts_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    signup_id = uuid4()
    row = SimpleNamespace(
        id=signup_id,
        email="person@example.com",
        status="pending",
        reviewed_at=None,
        reviewed_by=None,
        review_note=None,
    )
    session = MagicMock()
    session.get.return_value = row

    upsert = MagicMock(return_value=SimpleNamespace(email=row.email))
    notify = MagicMock()
    monkeypatch.setattr(admin_svc.allowlist_svc, "upsert_allowlist", upsert)
    monkeypatch.setattr(admin_svc, "notify_user_approved", notify)

    out, _allow = admin_svc.approve_waitlist(
        session,
        signup_id=signup_id,
        reviewed_by="test",
        notify_user=True,
    )

    assert out.status == "approved"
    upsert.assert_called_once()
    assert upsert.call_args.kwargs["email"] == "person@example.com"
    notify.assert_called_once_with(email="person@example.com")


def test_reject_revokes_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    signup_id = uuid4()
    row = SimpleNamespace(
        id=signup_id,
        email="person@example.com",
        status="pending",
        reviewed_at=None,
        reviewed_by=None,
        review_note=None,
    )
    session = MagicMock()
    session.get.return_value = row

    revoke = MagicMock(
        return_value=SimpleNamespace(email=row.email, revoked_at=datetime.now(UTC))
    )
    monkeypatch.setattr(admin_svc.allowlist_svc, "revoke_allowlist", revoke)

    out = admin_svc.reject_waitlist(
        session,
        signup_id=signup_id,
        reviewed_by="email-link",
        note="nope",
    )

    assert out.status == "rejected"
    assert out.reviewed_by == "email-link"
    revoke.assert_called_once_with(session, "person@example.com")


def test_reject_missing_signup() -> None:
    session = MagicMock()
    session.get.return_value = None
    with pytest.raises(AdminWaitlistError) as exc:
        admin_svc.reject_waitlist(session, signup_id=uuid4())
    assert exc.value.code == "not_found"
