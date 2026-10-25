"""Ingest public ATS list endpoints into ``job_posting`` (Phase 1).

Takes **no user id** — traffic grows with active boards, not users.

Greenhouse list URL often omits the JD body. Confirmed detail URL (live):
``https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{id}``
Lever / Ashby usually include description in the list payload.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Self
from urllib.parse import urlparse

import httpx
from sqlmodel import Session, col, select

from app.core.config import Settings, get_settings
from app.models.company_board import CompanyBoard
from app.models.job_posting import JobPosting
from app.services.html_text import html_to_plain_text
from app.services.job_match import apply_location_to_posting

logger = logging.getLogger(__name__)

# Public list endpoints (unauthenticated).
LIST_URL = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}
# Confirmed against live Discord / Stripe boards during Phase 1 research.
GREENHOUSE_DETAIL_URL = (
    "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}"
)


@dataclass
class ParsedListJob:
    """Normalized list-row identity (+ optional body from list payload)."""

    external_job_id: str
    title: str
    company_name: str
    location_raw: str
    apply_url: str | None
    vendor_posted_at: datetime | None
    vendor_updated_at: datetime | None
    # Raw body from list when the vendor includes it (Lever / Ashby).
    list_description_html_or_text: str | None
    # Hash input used when the vendor has no updated timestamp.
    list_content_fingerprint: str


@dataclass
class BoardIngestStats:
    board_id: str
    vendor: str
    slug: str
    ok: bool = False
    http_status: int | None = None
    listed: int = 0
    upserted: int = 0
    descriptions_written: int = 0
    descriptions_skipped: int = 0
    deactivated: int = 0
    quarantined: bool = False
    error: str | None = None


@dataclass
class IngestRunResult:
    boards_attempted: int = 0
    boards_ok: int = 0
    boards_failed: int = 0
    boards_quarantined: int = 0
    postings_upserted: int = 0
    descriptions_written: int = 0
    descriptions_skipped: int = 0
    deactivated: int = 0
    board_stats: list[BoardIngestStats] = field(default_factory=list)


def list_url_for(vendor: str, slug: str) -> str:
    template = LIST_URL.get(vendor)
    if not template:
        raise ValueError(f"unsupported vendor: {vendor}")
    return template.format(slug=slug)


def greenhouse_detail_url(slug: str, job_id: str) -> str:
    return GREENHOUSE_DETAIL_URL.format(slug=slug, job_id=job_id)


def _host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        # Lever createdAt is epoch ms.
        ts = float(value)
        if ts > 1e12:
            ts = ts / 1000.0
        return datetime.fromtimestamp(ts, tz=UTC)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        # Greenhouse uses offset without colon sometimes; fromisoformat is fine
        # for ISO-8601 with offset. Normalize Z.
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    return None


def _fingerprint(*parts: str | None) -> str:
    joined = "\n".join(p or "" for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _cap_description(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def parse_greenhouse_list(
    payload: dict[str, Any], *, board_company_name: str
) -> list[ParsedListJob]:
    jobs: list[ParsedListJob] = []
    for raw in payload.get("jobs") or []:
        if not isinstance(raw, dict):
            continue
        job_id = raw.get("id")
        if job_id is None:
            continue
        loc = raw.get("location") or {}
        location_raw = ""
        if isinstance(loc, dict):
            location_raw = str(loc.get("name") or "")
        elif isinstance(loc, str):
            location_raw = loc
        title = str(raw.get("title") or "")
        company = str(raw.get("company_name") or board_company_name or "")
        updated = _parse_dt(raw.get("updated_at"))
        posted = _parse_dt(raw.get("first_published"))
        apply_url = raw.get("absolute_url")
        apply = str(apply_url) if apply_url else None
        # List has no body — fingerprint identity fields for change hints.
        fp = _fingerprint(
            str(job_id),
            title,
            location_raw,
            apply or "",
            updated.isoformat() if updated else "",
            posted.isoformat() if posted else "",
        )
        jobs.append(
            ParsedListJob(
                external_job_id=str(job_id),
                title=title,
                company_name=company,
                location_raw=location_raw,
                apply_url=apply,
                vendor_posted_at=posted,
                vendor_updated_at=updated,
                list_description_html_or_text=None,
                list_content_fingerprint=fp,
            )
        )
    return jobs


def parse_lever_list(payload: Any, *, board_company_name: str) -> list[ParsedListJob]:
    rows = payload if isinstance(payload, list) else []
    jobs: list[ParsedListJob] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        job_id = raw.get("id")
        if not job_id:
            continue
        categories = raw.get("categories") or {}
        location_raw = ""
        if isinstance(categories, dict):
            location_raw = str(categories.get("location") or "")
        title = str(raw.get("text") or "")
        posted = _parse_dt(raw.get("createdAt"))
        # Lever list has no updatedAt — body change detected via hash.
        desc = (
            raw.get("descriptionPlain")
            or raw.get("descriptionBodyPlain")
            or raw.get("description")
            or raw.get("descriptionBody")
        )
        desc_s = str(desc) if desc else None
        apply = raw.get("hostedUrl") or raw.get("applyUrl")
        apply_s = str(apply) if apply else None
        fp = _fingerprint(
            str(job_id),
            title,
            location_raw,
            apply_s or "",
            desc_s or "",
            posted.isoformat() if posted else "",
        )
        jobs.append(
            ParsedListJob(
                external_job_id=str(job_id),
                title=title,
                company_name=board_company_name,
                location_raw=location_raw,
                apply_url=apply_s,
                vendor_posted_at=posted,
                vendor_updated_at=None,
                list_description_html_or_text=desc_s,
                list_content_fingerprint=fp,
            )
        )
    return jobs


def parse_ashby_list(
    payload: dict[str, Any], *, board_company_name: str
) -> list[ParsedListJob]:
    jobs: list[ParsedListJob] = []
    for raw in payload.get("jobs") or []:
        if not isinstance(raw, dict):
            continue
        job_id = raw.get("id")
        if not job_id:
            continue
        title = str(raw.get("title") or "")
        location_raw = str(raw.get("location") or "")
        if (
            raw.get("isRemote") is True
            and location_raw
            and "remote" not in location_raw.lower()
        ):
            location_raw = f"{location_raw} (Remote)"
        elif raw.get("isRemote") is True and not location_raw:
            location_raw = "Remote"
        posted = _parse_dt(raw.get("publishedAt"))
        updated = _parse_dt(raw.get("updatedAt"))
        desc = raw.get("descriptionPlain") or raw.get("descriptionHtml")
        desc_s = str(desc) if desc else None
        apply = raw.get("jobUrl") or raw.get("applyUrl")
        apply_s = str(apply) if apply else None
        stamp = updated or posted
        fp = _fingerprint(
            str(job_id),
            title,
            location_raw,
            apply_s or "",
            desc_s or "",
            stamp.isoformat() if stamp is not None else "",
        )
        jobs.append(
            ParsedListJob(
                external_job_id=str(job_id),
                title=title,
                company_name=board_company_name,
                location_raw=location_raw,
                apply_url=apply_s,
                vendor_posted_at=posted,
                vendor_updated_at=updated,
                list_description_html_or_text=desc_s,
                list_content_fingerprint=fp,
            )
        )
    return jobs


def parse_list_payload(
    vendor: str, payload: Any, *, board_company_name: str
) -> list[ParsedListJob]:
    if vendor == "greenhouse":
        if not isinstance(payload, dict):
            return []
        return parse_greenhouse_list(payload, board_company_name=board_company_name)
    if vendor == "lever":
        return parse_lever_list(payload, board_company_name=board_company_name)
    if vendor == "ashby":
        if not isinstance(payload, dict):
            return []
        return parse_ashby_list(payload, board_company_name=board_company_name)
    raise ValueError(f"unsupported vendor: {vendor}")


class AtsIngestService:
    """Manual / admin ingest over ``status=active`` boards. No user id."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self._client = http_client
        self._owns_client = http_client is None
        self._last_host_call_at: dict[str, float] = {}

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.settings.ingest_http_timeout_seconds,
                headers={"User-Agent": "UpdateApply-ingest/0.1 (+local; polite)"},
                follow_redirects=True,
            )
        return self._client

    def _polite_get(self, url: str) -> httpx.Response:
        """Serialize calls per host with a pause between requests."""
        host = _host_of(url)
        pause = float(self.settings.ingest_host_pause_seconds)
        if host and pause > 0:
            last = self._last_host_call_at.get(host)
            if last is not None:
                elapsed = time.monotonic() - last
                if elapsed < pause:
                    time.sleep(pause - elapsed)
        try:
            return self._http().get(url)
        finally:
            if host:
                self._last_host_call_at[host] = time.monotonic()

    def run(self, *, board_ids: list[Any] | None = None) -> IngestRunResult:
        """Ingest active boards. Optional ``board_ids`` limits the set."""
        result = IngestRunResult()
        boards = self._load_active_boards(board_ids)
        result.boards_attempted = len(boards)

        for board in boards:
            stats = self._ingest_board(board)
            result.board_stats.append(stats)
            if stats.ok:
                result.boards_ok += 1
            else:
                result.boards_failed += 1
            if stats.quarantined:
                result.boards_quarantined += 1
            result.postings_upserted += stats.upserted
            result.descriptions_written += stats.descriptions_written
            result.descriptions_skipped += stats.descriptions_skipped
            result.deactivated += stats.deactivated

        return result

    def _load_active_boards(self, board_ids: list[Any] | None) -> list[CompanyBoard]:
        stmt = select(CompanyBoard).where(CompanyBoard.status == "active")
        if board_ids:
            stmt = stmt.where(col(CompanyBoard.id).in_(board_ids))
        stmt = stmt.order_by(CompanyBoard.vendor, CompanyBoard.slug)
        return list(self.session.exec(stmt).all())

    def _ingest_board(self, board: CompanyBoard) -> BoardIngestStats:
        stats = BoardIngestStats(
            board_id=str(board.id),
            vendor=board.vendor,
            slug=board.slug,
        )
        url = list_url_for(board.vendor, board.slug)
        now = datetime.now(UTC)

        try:
            response = self._polite_get(url)
        except httpx.HTTPError as exc:
            stats.error = f"transport: {exc}"
            self._record_board_failure(board, stats.error, now, http_404=False)
            stats.quarantined = board.status == "unavailable"
            self.session.commit()
            return stats

        stats.http_status = response.status_code
        if response.status_code == 404:
            stats.error = "HTTP 404 (dead slug — not evidence the company left the ATS)"
            self._record_board_failure(board, stats.error, now, http_404=True)
            stats.quarantined = board.status == "unavailable"
            self.session.commit()
            return stats

        if response.status_code >= 400:
            stats.error = f"HTTP {response.status_code}"
            self._record_board_failure(board, stats.error, now, http_404=False)
            stats.quarantined = board.status == "unavailable"
            self.session.commit()
            return stats

        try:
            payload = response.json()
        except ValueError as exc:
            stats.error = f"invalid JSON: {exc}"
            self._record_board_failure(board, stats.error, now, http_404=False)
            stats.quarantined = board.status == "unavailable"
            self.session.commit()
            return stats

        parsed = parse_list_payload(
            board.vendor, payload, board_company_name=board.company_name
        )
        stats.listed = len(parsed)

        try:
            up, desc_w, desc_s, deact = self._upsert_postings(board, parsed, now)
            stats.upserted = up
            stats.descriptions_written = desc_w
            stats.descriptions_skipped = desc_s
            stats.deactivated = deact
            board.last_fetched_at = now
            board.last_error = None
            board.consecutive_failures = 0
            board.updated_at = now
            self.session.add(board)
            self.session.commit()
            stats.ok = True
        except Exception as exc:
            # Isolate one board's failure so the rest of the run continues.
            self.session.rollback()
            stats.error = f"upsert failed: {exc}"
            logger.exception("ingest upsert failed for %s/%s", board.vendor, board.slug)
            # Re-load board after rollback
            board = self.session.get(CompanyBoard, board.id) or board
            self._record_board_failure(board, stats.error, now, http_404=False)
            stats.quarantined = board.status == "unavailable"
            self.session.commit()

        return stats

    def _record_board_failure(
        self,
        board: CompanyBoard,
        error: str,
        now: datetime,
        *,
        http_404: bool,
    ) -> None:
        board.last_error = error[:2000]
        board.consecutive_failures = int(board.consecutive_failures or 0) + 1
        board.updated_at = now
        threshold = int(self.settings.ingest_failure_threshold)
        # 404 means this slug is dead; quarantine immediately.
        if http_404 or board.consecutive_failures >= threshold:
            board.status = "unavailable"
            # Stale directory slugs → 404 is expected at scale; keep off default INFO/WARNING.
            log = logger.debug if http_404 else logger.warning
            log(
                "quarantined board %s/%s after failure: %s",
                board.vendor,
                board.slug,
                error,
            )
        self.session.add(board)

    def _upsert_postings(
        self,
        board: CompanyBoard,
        parsed: list[ParsedListJob],
        now: datetime,
    ) -> tuple[int, int, int, int]:
        existing_rows = list(
            self.session.exec(
                select(JobPosting).where(JobPosting.board_id == board.id)
            ).all()
        )
        by_ext: dict[str, JobPosting] = {r.external_job_id: r for r in existing_rows}
        seen_ids: set[str] = set()
        upserted = 0
        desc_written = 0
        desc_skipped = 0
        max_chars = int(self.settings.ingest_description_max_chars)

        for job in parsed:
            seen_ids.add(job.external_job_id)
            row = by_ext.get(job.external_job_id)
            is_new = row is None
            if row is None:
                row = JobPosting(
                    board_id=board.id,
                    vendor=board.vendor,
                    external_job_id=job.external_job_id,
                    first_seen_at=now,
                )
                by_ext[job.external_job_id] = row

            row.company_name = job.company_name or board.company_name
            row.title = job.title
            incoming_location = job.location_raw or ""
            location_changed = (row.location_raw or "") != incoming_location
            row.location_raw = incoming_location
            if location_changed or row.location_parse_status is None:
                # Force re-parse when raw changes; leave a prior ok alone only
                # when raw is unchanged (apply_location_to_posting is idempotent).
                if location_changed:
                    row.location_parse_status = None
                    row.location_remote = None
                    row.location_countries = None
                apply_location_to_posting(row)
            row.apply_url = job.apply_url
            if job.vendor_posted_at is not None:
                row.vendor_posted_at = job.vendor_posted_at
            row.last_seen_at = now
            row.is_active = True
            row.updated_at = now

            need_body = self._should_store_description(
                row,
                is_new=is_new,
                incoming_updated_at=job.vendor_updated_at,
                incoming_fingerprint=job.list_content_fingerprint,
            )

            # Always refresh stored vendor_updated_at after the change check.
            if job.vendor_updated_at is not None:
                row.vendor_updated_at = job.vendor_updated_at

            if need_body:
                body_raw = job.list_description_html_or_text
                if body_raw is None and board.vendor == "greenhouse":
                    body_raw = self._fetch_greenhouse_description(
                        board.slug, job.external_job_id
                    )
                plain = html_to_plain_text(body_raw)
                plain, truncated = _cap_description(plain, max_chars)
                row.description_text = plain or None
                row.description_truncated = truncated if plain else False
                row.content_hash = job.list_content_fingerprint
                # Clear embedding so a later task can re-embed once.
                row.embedding = None
                desc_written += 1
            else:
                # Keep prior description_text / embedding / content_hash.
                desc_skipped += 1

            self.session.add(row)
            upserted += 1

        deactivated = 0
        for ext_id, row in by_ext.items():
            if ext_id not in seen_ids and row.is_active:
                row.is_active = False
                row.updated_at = now
                self.session.add(row)
                deactivated += 1

        return upserted, desc_written, desc_skipped, deactivated

    def _should_store_description(
        self,
        row: JobPosting,
        *,
        is_new: bool,
        incoming_updated_at: datetime | None,
        incoming_fingerprint: str,
    ) -> bool:
        if is_new:
            return True
        if row.description_text is None:
            return True
        if incoming_updated_at is not None:
            stored = row.vendor_updated_at
            if stored is None:
                return True
            # Normalize tz-aware compare.
            if stored.tzinfo is None:
                stored = stored.replace(tzinfo=UTC)
            incoming = incoming_updated_at
            if incoming.tzinfo is None:
                incoming = incoming.replace(tzinfo=UTC)
            return incoming != stored
        # No vendor timestamp — compare list fingerprint / content hash.
        return row.content_hash != incoming_fingerprint

    def _fetch_greenhouse_description(self, slug: str, job_id: str) -> str | None:
        url = greenhouse_detail_url(slug, job_id)
        try:
            response = self._polite_get(url)
        except httpx.HTTPError as exc:
            logger.warning("greenhouse detail transport error %s: %s", url, exc)
            return None
        if response.status_code != 200:
            logger.warning(
                "greenhouse detail HTTP %s for %s", response.status_code, url
            )
            return None
        try:
            data = response.json()
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        content = data.get("content")
        return str(content) if content else None
