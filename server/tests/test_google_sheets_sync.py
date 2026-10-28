"""Unit tests for Google Sheet id normalization (no network)."""

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
