"""Best-effort waitlist → Google Sheet sync via Composio.

Requires:
  WAITLIST_GOOGLE_SHEET_ID — spreadsheet ID (or full Sheets URL)
  COMPOSIO_API_KEY — Composio API key from the *same* project as the
    Google Sheets connection
  COMPOSIO_GOOGLE_SHEETS_ACCOUNT_ID — connected account id
    (e.g. googlesheets_nextly-fatima)

Missing config → log stub and return False (never fail signup).
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Prefer current REST API; v3 remains supported.
COMPOSIO_EXECUTE_URL = (
    "https://backend.composio.dev/api/v3.1/tools/execute/"
    "GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND"
)

_SHEET_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)")

CAREER_STAGE_LABELS = {
    "student": "Student / recent grad",
    "early_career": "Early career (0–2 years)",
    "mid_career": "Mid career (3–7 years)",
    "senior": "Senior (8+ years)",
    "career_changer": "Career changer",
    "other": "Other",
}


def normalize_spreadsheet_id(raw: str) -> str:
    """Accept a bare ID or a full docs.google.com spreadsheet URL."""
    value = raw.strip().strip('"').strip("'")
    if not value:
        return ""
    match = _SHEET_ID_RE.search(value)
    if match:
        return match.group(1)
    # Bare id (no path separators).
    if "/" not in value and " " not in value:
        return value
    return value


def _format_submitted_at(created_at: datetime | None) -> str:
    if created_at is None:
        return ""
    if created_at.tzinfo is None:
        dt = created_at.replace(tzinfo=UTC)
    else:
        dt = created_at.astimezone(UTC)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def append_waitlist_row(
    *,
    name: str,
    email: str,
    career_stage: str | None = None,
    job_search_challenges: str | None = None,
    source: str | None = None,
    signup_id: str | None = None,
    created_at: datetime | None = None,
    status: str = "pending",
    settings: Settings | None = None,
) -> bool:
    """Append one waitlist signup row to the shared Google Sheet."""
    settings = settings or get_settings()
    sheet_id = normalize_spreadsheet_id(settings.waitlist_google_sheet_id)
    api_key = settings.composio_api_key.strip().strip('"').strip("'")
    account_id = (
        settings.composio_google_sheets_account_id.strip().strip('"').strip("'")
    )
    range_a1 = settings.waitlist_google_sheet_range.strip() or "Sheet1!A:H"

    if not sheet_id or not api_key or not account_id:
        logger.warning(
            "google_sheets_sync skipped (missing config): "
            "sheet=%s key=%s account=%s email=%s",
            bool(sheet_id),
            bool(api_key),
            bool(account_id),
            email,
        )
        return False

    stage_label = CAREER_STAGE_LABELS.get(
        career_stage or "",
        career_stage or "",
    )
    values = [
        [
            _format_submitted_at(created_at),
            name,
            email,
            stage_label,
            job_search_challenges or "",
            source or "",
            status,
            signup_id or "",
        ]
    ]

    payload: dict[str, Any] = {
        "connected_account_id": account_id,
        "arguments": {
            "spreadsheetId": sheet_id,
            "range": range_a1,
            "values": values,
            "valueInputOption": "USER_ENTERED",
            "insertDataOption": "INSERT_ROWS",
        },
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                COMPOSIO_EXECUTE_URL,
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code >= 400:
            logger.warning(
                "Composio Sheets append failed status=%s body=%s "
                "(check COMPOSIO_API_KEY is from the same project as "
                "COMPOSIO_GOOGLE_SHEETS_ACCOUNT_ID=%s)",
                resp.status_code,
                resp.text[:400],
                account_id,
            )
            return False
        body = resp.json() if resp.content else {}
        if isinstance(body, dict) and body.get("successful") is False:
            logger.warning(
                "Composio Sheets append unsuccessful: %s",
                str(body.get("error") or body)[:400],
            )
            return False
        logger.info("google_sheets_sync ok email=%s sheet=%s", email, sheet_id)
        return True
    except (httpx.HTTPError, OSError, ValueError) as exc:
        logger.warning("Composio Sheets request error: %s", exc)
        return False
