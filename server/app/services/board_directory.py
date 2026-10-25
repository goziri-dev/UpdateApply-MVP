"""Import the full ATS Company Directory (CC-BY-4.0) into company_board.

Dataset: lastroundai-hiring-data / ats-directory (DataHub + Kaggle).
Attribution: see ``server/data/ATTRIBUTION-ats-company-directory.md``.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from sqlmodel import Session, select

from app.models.company_board import VENDOR_VALUES, CompanyBoard

logger = logging.getLogger(__name__)

_UNIT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIRECTORY_PATH = (
    _UNIT_ROOT / "data" / "seeds" / "lastroundai-ats-company-directory-2026-08.csv"
)

# Canonical CSV used by TSK-29 research (CC-BY-4.0).
DIRECTORY_CSV_URL = (
    "https://datahub.io/lastroundai-hiring-data/lastroundai-hiring-data/"
    "_r/-/ats-directory/lastroundai-ats-company-directory-2026-08.csv"
)

VENDOR_ALIASES = {
    "greenhouse": "greenhouse",
    "lever": "lever",
    "ashby": "ashby",
}


@dataclass
class DirectoryImportResult:
    total_rows: int = 0
    inserted: int = 0
    updated: int = 0
    skipped_vendor: int = 0
    skipped_bad: int = 0
    errors: list[str] = field(default_factory=list)


def download_directory_csv(
    dest: Path | None = None,
    *,
    url: str = DIRECTORY_CSV_URL,
) -> Path:
    """Download the public directory CSV into ``data/seeds/`` (or ``dest``)."""
    path = dest or DEFAULT_DIRECTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    req = Request(
        url,
        headers={"User-Agent": "UpdateApply-directory-import/0.1 (+local; CC-BY-4.0)"},
    )
    with urlopen(req, timeout=120) as resp:
        data = resp.read()
    path.write_bytes(data)
    logger.info("wrote directory CSV to %s (%s bytes)", path, len(data))
    return path


def load_directory_rows(path: Path) -> list[dict[str, Any]]:
    """Parse CSV columns ``ats_vendor``, ``company_name``, ``board_slug``."""
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict[str, Any]] = []
    for raw in reader:
        rows.append(
            {
                "vendor": (raw.get("ats_vendor") or raw.get("vendor") or "").strip(),
                "slug": (raw.get("board_slug") or raw.get("slug") or "").strip(),
                "company_name": (
                    raw.get("company_name") or raw.get("name") or ""
                ).strip(),
            }
        )
    return rows


def upsert_directory_boards(
    session: Session,
    rows: list[dict[str, Any]],
) -> DirectoryImportResult:
    """Upsert directory rows. Does not fetch jobs.

    Rules:
    - Upsert key ``(vendor, slug)``.
    - New rows: ``status=active``, ``source=seed``.
    - Existing ``source=user`` stays ``user``; company_name updates only if empty.
    - Unknown vendors are skipped and counted.
    """
    result = DirectoryImportResult(total_rows=len(rows))
    now = datetime.now(UTC)

    for index, row in enumerate(rows):
        raw_vendor = str(row.get("vendor") or "").strip().lower()
        vendor = VENDOR_ALIASES.get(raw_vendor)
        if vendor is None or vendor not in VENDOR_VALUES:
            result.skipped_vendor += 1
            continue

        slug = str(row.get("slug") or "").strip()
        company_name = str(row.get("company_name") or "").strip()
        if not slug:
            msg = f"row {index}: empty slug"
            result.skipped_bad += 1
            result.errors.append(msg)
            continue
        if not company_name:
            msg = f"row {index}: empty company_name for {vendor}/{slug}"
            result.skipped_bad += 1
            result.errors.append(msg)
            continue

        existing = session.exec(
            select(CompanyBoard).where(
                CompanyBoard.vendor == vendor,
                CompanyBoard.slug == slug,
            )
        ).first()

        if existing is None:
            session.add(
                CompanyBoard(
                    vendor=vendor,
                    slug=slug,
                    company_name=company_name,
                    status="active",
                    source="seed",
                    created_at=now,
                    updated_at=now,
                )
            )
            result.inserted += 1
            continue

        changed = False
        if existing.source == "user":
            if not (existing.company_name or "").strip():
                existing.company_name = company_name
                changed = True
            # Keep source=user; do not revive unavailable via directory alone.
        else:
            if existing.company_name != company_name:
                existing.company_name = company_name
                changed = True
            if existing.source != "seed":
                existing.source = "seed"
                changed = True

        if changed:
            existing.updated_at = now
            session.add(existing)
            result.updated += 1

    session.commit()
    return result
