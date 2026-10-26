"""Unit tests for signed waitlist approve/reject tokens."""

from uuid import uuid4

import pytest

from app.core.config import Settings
from app.services.admin_action_token import (
    AdminActionTokenError,
    sign_waitlist_action,
    verify_waitlist_action,
)


def _settings(**kwargs: str) -> Settings:
    base = {
        "admin_api_key": "test-admin-secret",
        "api_public_url": "https://api.updateapply.com",
    }
    base.update(kwargs)
    return Settings(**base)


def test_sign_and_verify_roundtrip() -> None:
    settings = _settings()
    signup_id = uuid4()
    token = sign_waitlist_action(
        settings, signup_id=signup_id, action="approve", now=1_700_000_000
    )
    verify_waitlist_action(
        settings,
        signup_id=signup_id,
        action="approve",
        token=token,
        now=1_700_000_000,
    )


def test_reject_token_not_valid_for_approve() -> None:
    settings = _settings()
    signup_id = uuid4()
    token = sign_waitlist_action(
        settings, signup_id=signup_id, action="reject", now=1_700_000_000
    )
    with pytest.raises(AdminActionTokenError, match="signature"):
        verify_waitlist_action(
            settings,
            signup_id=signup_id,
            action="approve",
            token=token,
            now=1_700_000_000,
        )


def test_wrong_signup_id_rejected() -> None:
    settings = _settings()
    token = sign_waitlist_action(
        settings, signup_id=uuid4(), action="approve", now=1_700_000_000
    )
    with pytest.raises(AdminActionTokenError, match="signature"):
        verify_waitlist_action(
            settings,
            signup_id=uuid4(),
            action="approve",
            token=token,
            now=1_700_000_000,
        )


def test_expired_token_rejected() -> None:
    settings = _settings()
    signup_id = uuid4()
    token = sign_waitlist_action(
        settings,
        signup_id=signup_id,
        action="approve",
        ttl_seconds=60,
        now=1_700_000_000,
    )
    with pytest.raises(AdminActionTokenError, match="expired"):
        verify_waitlist_action(
            settings,
            signup_id=signup_id,
            action="approve",
            token=token,
            now=1_700_000_000 + 120,
        )


def test_tampered_sig_rejected() -> None:
    settings = _settings()
    signup_id = uuid4()
    token = sign_waitlist_action(
        settings, signup_id=signup_id, action="approve", now=1_700_000_000
    )
    exp, _sig = token.split(".", 1)
    with pytest.raises(AdminActionTokenError, match="signature"):
        verify_waitlist_action(
            settings,
            signup_id=signup_id,
            action="approve",
            token=f"{exp}.{'0' * 64}",
            now=1_700_000_000,
        )


def test_sign_requires_admin_key() -> None:
    settings = _settings(admin_api_key="")
    with pytest.raises(AdminActionTokenError, match="ADMIN_API_KEY"):
        sign_waitlist_action(settings, signup_id=uuid4(), action="approve")
