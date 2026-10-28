"""Unit tests for Google Sheet sync (no network)."""

from typing import Any, Self

from app.core.config import Settings
from app.services import google_sheets_sync
from app.services.google_sheets_sync import normalize_spreadsheet_id


def test_normalize_bare_id() -> None:
    sid = "1h3SpdJP8Zk03uSb5SZPBJz2AVeS9qcneW_iBk16C2XQ"
    assert normalize_spreadsheet_id(sid) == sid


def test_normalize_full_url() -> None:
    sid = "1h3SpdJP8Zk03uSb5SZPBJz2AVeS9qcneW_iBk16C2XQ"
    url = f"https://docs.google.com/spreadsheets/d/{sid}/edit#gid=0"
    assert normalize_spreadsheet_id(url) == sid


def test_normalize_strips_quotes() -> None:
    sid = "1h3SpdJP8Zk03uSb5SZPBJz2AVeS9qcneW_iBk16C2XQ"
    assert normalize_spreadsheet_id(f'"{sid}"') == sid


def test_append_sends_user_id_with_connected_account(monkeypatch: Any) -> None:
    request: dict[str, Any] = {}

    class FakeResponse:
        status_code = 200
        content = b"{}"

        @staticmethod
        def json() -> dict[str, Any]:
            return {}

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            assert timeout == 20.0

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def post(self, url: str, **kwargs: Any) -> FakeResponse:
            request.update(url=url, **kwargs)
            return FakeResponse()

    monkeypatch.setattr(google_sheets_sync.httpx, "Client", FakeClient)
    settings = Settings(
        waitlist_google_sheet_id="sheet-id",
        composio_api_key="api-key",
        composio_google_sheets_account_id="account-id",
        composio_user_id="user-id",
    )

    assert google_sheets_sync.append_waitlist_row(
        name="Smoke Test",
        email="smoke@example.com",
        settings=settings,
    )
    assert request["json"]["connected_account_id"] == "account-id"
    assert request["json"]["user_id"] == "user-id"


def test_append_skips_when_user_id_is_missing(monkeypatch: Any) -> None:
    def fail_client(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("HTTP client should not be created")

    monkeypatch.setattr(google_sheets_sync.httpx, "Client", fail_client)
    settings = Settings(
        waitlist_google_sheet_id="sheet-id",
        composio_api_key="api-key",
        composio_google_sheets_account_id="account-id",
        composio_user_id="",
    )

    assert not google_sheets_sync.append_waitlist_row(
        name="Smoke Test",
        email="smoke@example.com",
        settings=settings,
    )
