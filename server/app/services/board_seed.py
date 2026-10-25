"""Load a bounded ``company_board`` seed from a data file (Phase 1)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app.models.company_board import VENDOR_VALUES, CompanyBoard

logger = logging.getLogger(__name__)

_UNIT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED_PATH = _UNIT_ROOT / "data" / "seeds" / "company_boards.json"


@dataclass
class SeedLoadResult:
    inserted: int = 0
    updated: int = 0
    skipped_bad: int = 0
    errors: list[str] = field(default_factory=list)
    total_rows: int = 0


def load_seed_file(path: Path | None = None) -> list[dict[str, Any]]:
    seed_path = path or DEFAULT_SEED_PATH
    raw = json.loads(seed_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise TypeError(f"Seed file must be a JSON array: {seed_path}")
    return raw


def upsert_company_boards(
    session: Session,
    rows: list[dict[str, Any]],
    *,
    source: str = "seed",
) -> SeedLoadResult:
    """Upsert boards on ``(vendor, slug)``. Bad rows are reported, not fatal."""
    result = SeedLoadResult(total_rows=len(rows))
    now = datetime.now(UTC)

    for index, row in enumerate(rows):
        vendor = str(row.get("vendor") or "").strip().lower()
        slug = str(row.get("slug") or "").strip()
        company_name = str(row.get("company_name") or "").strip()

        if vendor not in VENDOR_VALUES:
            msg = f"row {index}: unknown vendor {vendor!r}"
            result.skipped_bad += 1
            result.errors.append(msg)
            logger.warning(msg)
            continue
        if not slug:
            msg = f"row {index}: empty slug"
            result.skipped_bad += 1
            result.errors.append(msg)
            logger.warning(msg)
            continue
        if not company_name:
            msg = f"row {index}: empty company_name for {vendor}/{slug}"
            result.skipped_bad += 1
            result.errors.append(msg)
            logger.warning(msg)
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
                    source=source,
                    created_at=now,
                    updated_at=now,
                )
            )
            result.inserted += 1
        else:
            existing.company_name = company_name
            # Do not revive unavailable/disabled via seed; only refresh name/source.
            if existing.source != source:
                existing.source = source
            existing.updated_at = now
            session.add(existing)
            result.updated += 1

    session.commit()
    return result
