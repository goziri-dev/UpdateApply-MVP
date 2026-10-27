"""Unit tests for Favour waitlist notify email content (no Resend)."""

from datetime import UTC, datetime
from uuid import UUID

from app.core.config import Settings
from app.services.email_notify import (
    build_favour_waitlist_email,
    build_waitlist_action_urls,
)

SIGNUP_ID = UUID("11111111-1111-1111-1111-111111111111")
CREATED = datetime(2026, 10, 26, 20, 0, 0, tzinfo=UTC)


def _settings(*, admin_key: str = "test-admin-secret") -> Settings:
    return Settings(
        admin_api_key=admin_key,
        api_public_url="https://api.updateapply.com",
        resend_api_key="",
        admin_notify_email="",
    )


def test_email_includes_fields_and_action_links() -> None:
    settings = _settings()
    subject, text, html = build_favour_waitlist_email(
        email="person@example.com",
        name="Ada Lovelace",
        career_stage="early_career",
        job_search_challenges="Tailoring resumes",
        source="landing",
        signup_id=SIGNUP_ID,
        created_at=CREATED,
        settings=settings,
    )
    assert "person@example.com" in subject
    assert "New waitlist signup" in subject
    assert "Name: Ada Lovelace" in text
    assert "Email: person@example.com" in text
    assert "Career stage: early_career" in text
    assert "Job-search challenges: Tailoring resumes" in text
    assert "Source: landing" in text
    assert str(SIGNUP_ID) in text
    assert "Submitted at:" in text
    assert "Approve" in text
    assert "Reject" in text
    assert "ADMIN_API_KEY" not in text
    assert "X-Admin-Key" not in text
    assert "curl" not in text.lower()

    assert html is not None
    assert "Ada Lovelace" in html
    assert "person@example.com" in html
    assert "early_career" in html
    assert "Approve" in html
    assert "Reject" in html
    assert f"/api/v1/admin/waitlist/{SIGNUP_ID}/approve?t=" in html
    assert f"/api/v1/admin/waitlist/{SIGNUP_ID}/reject?t=" in html
    assert "ADMIN_API_KEY" not in html
    assert "curl" not in html.lower()


def test_action_urls_signed_and_distinct() -> None:
    settings = _settings()
    approve, reject = build_waitlist_action_urls(settings, signup_id=SIGNUP_ID)
    assert approve is not None and reject is not None
    assert approve.startswith(
        f"https://api.updateapply.com/api/v1/admin/waitlist/{SIGNUP_ID}/approve?t="
    )
    assert reject.startswith(
        f"https://api.updateapply.com/api/v1/admin/waitlist/{SIGNUP_ID}/reject?t="
    )
    assert approve.split("t=")[1] != reject.split("t=")[1]


def test_no_links_without_admin_key() -> None:
    settings = _settings(admin_key="")
    approve, reject = build_waitlist_action_urls(settings, signup_id=SIGNUP_ID)
    assert approve is None and reject is None
    _subject, text, html = build_favour_waitlist_email(
        email="person@example.com",
        source=None,
        signup_id=SIGNUP_ID,
        created_at=CREATED,
        settings=settings,
    )
    assert "unavailable" in text.lower()
    assert html is not None
    assert "unavailable" in html.lower()
    assert "Source: unknown" in text
