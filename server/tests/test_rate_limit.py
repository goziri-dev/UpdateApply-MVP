"""Unit tests for LLM route rate limiting (no DB / no HTTP app)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.core.rate_limit import (
    check_rate_limit,
    enforce_user_rate_limit,
    reset_rate_limit_state,
)


@pytest.fixture(autouse=True)
def _clear_hits() -> None:
    reset_rate_limit_state()
    yield
    reset_rate_limit_state()


def _settings(**kwargs: int) -> Settings:
    return Settings.model_construct(**kwargs)


def test_allows_under_limit() -> None:
    for _ in range(3):
        allowed, retry = check_rate_limit("u1", limit=3, window_s=60.0, now=100.0)
        assert allowed is True
        assert retry == 0.0


def test_blocks_at_limit_and_reports_retry() -> None:
    now = 1_000.0
    for _ in range(2):
        allowed, _ = check_rate_limit("u2", limit=2, window_s=60.0, now=now)
        assert allowed is True
        now += 1.0

    allowed, retry = check_rate_limit("u2", limit=2, window_s=60.0, now=now)
    assert allowed is False
    # Oldest hit at 1000, window 60 → retry ≈ 58 from now=1002
    assert 57.0 <= retry <= 59.0


def test_window_expiry_frees_slot() -> None:
    check_rate_limit("u3", limit=1, window_s=10.0, now=0.0)
    allowed, _ = check_rate_limit("u3", limit=1, window_s=10.0, now=5.0)
    assert allowed is False

    allowed, retry = check_rate_limit("u3", limit=1, window_s=10.0, now=10.0)
    assert allowed is True
    assert retry == 0.0


def test_keys_are_independent() -> None:
    check_rate_limit("a", limit=1, window_s=60.0, now=0.0)
    allowed, _ = check_rate_limit("b", limit=1, window_s=60.0, now=0.0)
    assert allowed is True


def test_limit_zero_disables() -> None:
    for _ in range(5):
        allowed, retry = check_rate_limit("off", limit=0, window_s=60.0)
        assert allowed is True
        assert retry == 0.0


def test_enforce_raises_429_with_retry_after() -> None:
    settings = _settings(
        llm_rate_limit_heavy=1,
        llm_rate_window_seconds_heavy=120,
        llm_rate_limit_standard=40,
        llm_rate_window_seconds_standard=600,
    )
    enforce_user_rate_limit(user_id="user-a", tier="heavy", settings=settings)

    with pytest.raises(HTTPException) as exc:
        enforce_user_rate_limit(user_id="user-a", tier="heavy", settings=settings)

    assert exc.value.status_code == 429
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail["error"] == "rate_limited"
    assert detail["tier"] == "heavy"
    assert int(detail["retry_after_seconds"]) >= 1
    assert exc.value.headers is not None
    assert "Retry-After" in exc.value.headers


def test_heavy_and_standard_buckets_are_separate() -> None:
    settings = _settings(
        llm_rate_limit_heavy=1,
        llm_rate_window_seconds_heavy=600,
        llm_rate_limit_standard=1,
        llm_rate_window_seconds_standard=600,
    )
    enforce_user_rate_limit(user_id="user-b", tier="heavy", settings=settings)
    # Standard still open after heavy is exhausted.
    enforce_user_rate_limit(user_id="user-b", tier="standard", settings=settings)

    with pytest.raises(HTTPException):
        enforce_user_rate_limit(user_id="user-b", tier="standard", settings=settings)
