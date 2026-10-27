"""Best-effort waitlist → Google Sheet sync via Composio.

Requires:
  WAITLIST_GOOGLE_SHEET_ID — spreadsheet ID (from the shared sheet URL)
  COMPOSIO_API_KEY — Composio API key
  COMPOSIO_GOOGLE_SHEETS_ACCOUNT_ID — connected Google Sheets account id

Missing config → log stub and return False (never fail signup).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

COMPOSIO_EXECUTE_URL = (
    "https://backend.composio.dev/api/v3/tools/execute/"
    "GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND"
)

CAREER_STAGE_LABELS = {
    "student": "Student / recent grad",
    "early_career": "Early career (0–2 years)",
    "mid_career": "Mid career (3–7 years)",
    "senior": "Senior (8+ years)",
    "career_changer": "Career changer",
    "other": "Other",
}


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
    sheet_id = settings.waitlist_google_sheet_id.strip()
    api_key = settings.composio_api_key.strip()
    account_id = settings.composio_google_sheets_account_id.strip()
    range_a1 = settings.waitlist_google_sheet_range.strip() or "Sheet1!A:H"

    if not sheet_id or not api_key or not account_id:
        logger.info(
            "google_sheets_sync stub (missing config): email=%s sheet=%s",
            email,
            bool(sheet_id),
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
            # Composio GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND schema (camelCase).
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
                "Composio Sheets append failed status=%s body=%s",
                resp.status_code,
                resp.text[:300],
            )
            return False
        body = resp.json() if resp.content else {}
        if isinstance(body, dict) and body.get("successful") is False:
            logger.warning(
                "Composio Sheets append unsuccessful: %s",
                str(body.get("error") or body)[:300],
            )
            return False
        return True
    except (httpx.HTTPError, OSError, ValueError) as exc:
        logger.warning("Composio Sheets request error: %s", exc)
        return False
