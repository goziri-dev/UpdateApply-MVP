"""Unit tests for allowlist email normalize / gate helpers (no DB)."""

from app.services.waitlist import normalize_email


def test_normalize_for_allowlist_match() -> None:
    assert normalize_email("  Me@UpdateApply.COM ") == "me@updateapply.com"
