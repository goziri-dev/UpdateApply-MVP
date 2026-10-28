"""Unit tests for waitlist normalize / validate (no DB)."""

import pytest

from app.services.waitlist import (
    WaitlistValidationError,
    normalize_email,
    normalize_name,
    validate_career_stage,
    validate_challenges,
    validate_email,
    validate_name,
)


def test_normalize_email_lower_and_strip() -> None:
    assert normalize_email("  Foo@Example.COM ") == "foo@example.com"


def test_normalize_name_collapses_spaces() -> None:
    assert normalize_name("  Ada   Lovelace ") == "Ada Lovelace"


def test_validate_email_ok() -> None:
    validate_email("person@example.com")


def test_validate_email_empty() -> None:
    with pytest.raises(WaitlistValidationError) as exc:
        validate_email("")
    assert exc.value.code == "invalid_email"


def test_validate_email_bad() -> None:
    with pytest.raises(WaitlistValidationError) as exc:
        validate_email("not-an-email")
    assert exc.value.code == "invalid_email"


def test_validate_name_ok() -> None:
    validate_name("Ada Lovelace")


def test_validate_name_empty() -> None:
    with pytest.raises(WaitlistValidationError) as exc:
        validate_name("")
    assert exc.value.code == "invalid_name"


def test_validate_career_stage_ok() -> None:
    validate_career_stage("early_career")


def test_validate_career_stage_bad() -> None:
    with pytest.raises(WaitlistValidationError) as exc:
        validate_career_stage("intern")
    assert exc.value.code == "invalid_career_stage"


def test_validate_challenges_optional() -> None:
    assert validate_challenges(None) is None
    assert validate_challenges("  ") is None
    assert validate_challenges("  Finding roles  ") == "Finding roles"


def test_validate_challenges_too_long() -> None:
    with pytest.raises(WaitlistValidationError) as exc:
        validate_challenges("x" * 1001)
    assert exc.value.code == "invalid_challenges"
