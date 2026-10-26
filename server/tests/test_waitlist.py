"""Unit tests for waitlist normalize / validate (no DB)."""

import pytest

from app.services.waitlist import (
    WaitlistValidationError,
    normalize_email,
    validate_email,
)


def test_normalize_email_lower_and_strip() -> None:
    assert normalize_email("  Foo@Example.COM ") == "foo@example.com"


def test_validate_email_ok() -> None:
    validate_email("person@example.com")


def test_validate_email_empty() -> None:
    with pytest.raises(WaitlistValidationError):
        validate_email("")


def test_validate_email_bad() -> None:
    with pytest.raises(WaitlistValidationError):
        validate_email("not-an-email")
