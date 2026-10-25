"""Detect Greenhouse / Lever / Ashby boards from a pasted careers URL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlmodel import Session, select

from app.models.company_board import CompanyBoard

# Host → vendor. Path segment 0 is the board slug.
_HOST_VENDOR: dict[str, str] = {
    "boards.greenhouse.io": "greenhouse",
    "job-boards.greenhouse.io": "greenhouse",
    "boards-api.greenhouse.io": "greenhouse",
    "jobs.lever.co": "lever",
    "api.lever.co": "lever",
    "jobs.ashbyhq.com": "ashby",
    "api.ashbyhq.com": "ashby",
}


class BoardDetectError(Exception):
    def __init__(self, message: str, *, code: str = "unsupported_board") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True)
class DetectedBoard:
    vendor: str
    slug: str
    company_name: str


@dataclass
class UpsertFromUrlResult:
    board: CompanyBoard
    created: bool
    reactivated: bool


def parse_careers_url(url: str) -> DetectedBoard:
    """Host-only detection. Does not fetch the page or follow redirects."""
    raw = (url or "").strip()
    if not raw:
        raise BoardDetectError(
            "Paste a Greenhouse, Lever, or Ashby careers URL.",
            code="unsupported_board",
        )

    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").lower().removeprefix("www.")
    vendor = _HOST_VENDOR.get(host)
    if vendor is None:
        raise BoardDetectError(
            "Could not find a Greenhouse, Lever, or Ashby board in that URL. "
            "Paste a link from boards.greenhouse.io, jobs.lever.co, or "
            "jobs.ashbyhq.com — we do not scrape company career sites.",
            code="unsupported_board",
        )

    parts = [p for p in (parsed.path or "").split("/") if p]
    # Ashby posting-api path: /posting-api/job-board/{slug}
    if (
        host == "api.ashbyhq.com"
        and len(parts) >= 3
        and parts[0] == "posting-api"
        or host == "api.lever.co"
        and len(parts) >= 3
        and parts[0] == "v0"
        or host == "boards-api.greenhouse.io"
        and len(parts) >= 3
        and parts[0] == "v1"
    ):
        slug = parts[2]
    else:
        slug = parts[0] if parts else ""

    slug = slug.strip()
    if not slug or slug in {"jobs", "embed", "v1", "v0", "posting-api"}:
        raise BoardDetectError(
            "That URL is missing a board slug in the path.",
            code="unsupported_board",
        )

    # Display name: humanize slug until ingest/directory supplies a better one.
    company_name = slug.replace("-", " ").replace("_", " ").strip().title()
    return DetectedBoard(vendor=vendor, slug=slug, company_name=company_name)


def upsert_board_from_url(session: Session, url: str) -> UpsertFromUrlResult:
    """Insert or revive a company_board. Does not fetch ATS jobs."""
    detected = parse_careers_url(url)
    now = datetime.now(UTC)
    existing = session.exec(
        select(CompanyBoard).where(
            CompanyBoard.vendor == detected.vendor,
            CompanyBoard.slug == detected.slug,
        )
    ).first()

    if existing is None:
        board = CompanyBoard(
            vendor=detected.vendor,
            slug=detected.slug,
            company_name=detected.company_name,
            status="active",
            source="user",
            consecutive_failures=0,
            last_error=None,
            created_at=now,
            updated_at=now,
        )
        session.add(board)
        session.commit()
        session.refresh(board)
        return UpsertFromUrlResult(board=board, created=True, reactivated=False)

    reactivated = False
    if existing.status == "unavailable":
        existing.status = "active"
        existing.consecutive_failures = 0
        existing.last_error = None
        reactivated = True
    # Keep seed source; user paste still revives. Do not demote source=user.
    if not (existing.company_name or "").strip():
        existing.company_name = detected.company_name
    existing.updated_at = now
    session.add(existing)
    session.commit()
    session.refresh(existing)
    return UpsertFromUrlResult(
        board=existing,
        created=False,
        reactivated=reactivated,
    )
