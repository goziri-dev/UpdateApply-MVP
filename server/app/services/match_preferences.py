"""Read / replace confirmed Match Preferences (Phase 0 / TSK-27)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.models.match_preference import MatchPreference

ALLOWED_REMOTE = frozenset({"remote_only", "remote_ok", "onsite_only"})
ALLOWED_SENIORITY = frozenset(
    {
        "intern",
        "junior",
        "mid",
        "senior",
        "staff_principal",
        "lead_manager",
    }
)


class MatchPreferenceError(Exception):
    def __init__(self, message: str, *, code: str = "invalid_preferences") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def get_for_user(session: Session, user_id: UUID) -> MatchPreference | None:
    return session.exec(
        select(MatchPreference).where(MatchPreference.user_id == user_id)
    ).first()


def delete_for_user(session: Session, user_id: UUID) -> bool:
    """Remove saved Job preferences. Returns True if a row was deleted."""
    row = get_for_user(session, user_id)
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True


def normalize_titles(raw: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        title = " ".join(str(item).split()).strip()
        if not title:
            continue
        key = title.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(title)
    return out


def normalize_countries(raw: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        country = " ".join(str(item).split()).strip()
        if not country:
            continue
        key = country.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(country)
    return out


def normalize_seniority(raw: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        band = str(item).strip()
        if band not in ALLOWED_SENIORITY:
            raise MatchPreferenceError(
                f"Unknown seniority band: {band}",
                code="invalid_seniority",
            )
        if band in seen:
            continue
        seen.add(band)
        out.append(band)
    return out


def replace_for_user(
    session: Session,
    user_id: UUID,
    *,
    titles: list[str],
    seniority_bands: list[str],
    remote_preference: str,
    countries: list[str],
    city: str | None,
) -> MatchPreference:
    clean_titles = normalize_titles(titles)
    if not clean_titles:
        raise MatchPreferenceError(
            "Add at least one preferred title.",
            code="missing_titles",
        )
    clean_seniority = normalize_seniority(seniority_bands)
    if not clean_seniority:
        raise MatchPreferenceError(
            "Pick at least one seniority band.",
            code="missing_seniority",
        )
    if remote_preference not in ALLOWED_REMOTE:
        raise MatchPreferenceError(
            "Pick a remote preference.",
            code="invalid_remote",
        )
    clean_countries = normalize_countries(countries)
    clean_city = " ".join((city or "").split()).strip() or None

    now = datetime.now(UTC)
    row = get_for_user(session, user_id)
    if row is None:
        row = MatchPreference(
            id=uuid4(),
            user_id=user_id,
            titles=clean_titles,
            seniority_bands=clean_seniority,
            remote_preference=remote_preference,
            countries=clean_countries,
            city=clean_city,
            confirmed_at=now,
            updated_at=now,
        )
        session.add(row)
    else:
        row.titles = clean_titles
        row.seniority_bands = clean_seniority
        row.remote_preference = remote_preference
        row.countries = clean_countries
        row.city = clean_city
        row.confirmed_at = now
        row.updated_at = now
        session.add(row)

    session.commit()
    session.refresh(row)
    return row
