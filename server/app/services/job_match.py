"""Filter + score job_posting rows for Jobs For You (Phase 2).

Pass 1: confirmed titles / place / seniority + lookback (no embeddings).
Pass 2: max cosine vs the user's profile_chunk rows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import ColumnElement, and_, bindparam, or_, text
from sqlalchemy import func as sa_func
from sqlalchemy.orm import defer
from sqlmodel import Session, col, select

from app.core.config import Settings, get_settings
from app.models.job_posting import JobPosting
from app.models.match_ledger import MatchLedger
from app.models.match_preference import MatchPreference
from app.models.profile_chunk import ProfileChunk
from app.services.embeddings import EmbeddingsClient, get_embeddings_client
from app.services.location_normalize import country_code_for, normalize_location

# Approximate — Greenhouse often exposes updated_at, not first published.
DEFAULT_LOOKBACK_HOURS = 48
DEFAULT_SHORTLIST_CAP = 10
# Request path must stay interactive; daily / backfill_embeddings owns vectors.
MAX_REQUEST_PATH_EMBEDS = 0
# Cap how many already-embedded hits get a cosine Pass-2 score (rest: weak).
MAX_VECTOR_SCORE_CANDIDATES = 80
# Leading excerpt for posting embeddings (title is always prefixed).
_EMBED_EXCERPT_CHARS = 4_000

_SENIORITY_TOKENS = frozenset(
    {
        "intern",
        "internship",
        "junior",
        "jr",
        "jr.",
        "mid",
        "middle",
        "senior",
        "sr",
        "sr.",
        "staff",
        "principal",
        "lead",
        "manager",
        "director",
        "head",
        "vp",
        "vice",
        "chief",
    }
)
_STOP_TOKENS = frozenset({"and", "the", "of", "for", "a", "an", "to", "in", "on"})

# Shared domain stem + a role suffix → treat as the same hiring family.
_DOMAIN_STEMS = frozenset(
    {
        "marketing",
        "content",
        "social",
        "media",
        "brand",
        "growth",
        "community",
        "design",
        "product",
        "sales",
        "engineering",
        "software",
        "frontend",
        "backend",
        "fullstack",
        "full-stack",
        "data",
        "security",
        "platform",
        "devops",
        "recruiting",
        "recruiter",
        "support",
        "success",
    }
)
_ROLE_SUFFIXES = frozenset(
    {
        "manager",
        "specialist",
        "coordinator",
        "analyst",
        "associate",
        "director",
        "lead",
        "engineer",
        "developer",
        "designer",
        "creator",
        "producer",
        "writer",
        "recruiter",
        "sourcer",
    }
)

# Stems in the same group count as a shared domain (social ↔ marketing).
# Omit "growth" — ATS often appends it as an eng team ("Software Engineer, Growth").
_RELATED_STEM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"marketing", "content", "social", "media", "brand", "community"}),
)

# Band → tokens that *belong* to that band (explicit match boosts later).
_BAND_TOKENS: dict[str, frozenset[str]] = {
    "intern": frozenset({"intern", "internship"}),
    "junior": frozenset({"junior", "jr", "jr."}),
    "mid": frozenset({"mid", "middle"}),
    "senior": frozenset({"senior", "sr", "sr."}),
    "staff_principal": frozenset({"staff", "principal"}),
    "lead_manager": frozenset(
        {"lead", "manager", "director", "head", "vp", "vice", "chief"}
    ),
}

# Clear contradictions: posting token set vs user IC / manager bands.
_JUNIORISH = frozenset({"intern", "internship", "junior", "jr", "jr."})
_SENIORISH = frozenset(
    {
        "senior",
        "sr",
        "sr.",
        "staff",
        "principal",
        "lead",
        "manager",
        "director",
        "head",
        "vp",
        "vice",
        "chief",
    }
)
# People-manager / exec signals only — bare "manager" is kept out because ATS
# titles like "Product Marketing Manager" are usually IC / function leads.
_MANAGERISH = frozenset({"director", "head", "vp", "vice", "chief"})
_PEOPLE_MANAGER_TITLE = frozenset({"engineering", "engineer"})
_MANAGER_BANDS = frozenset({"lead_manager"})


@dataclass(frozen=True, slots=True)
class EligibleHit:
    posting: JobPosting
    matched_title: str
    location_phrase: str
    seniority_explicit: bool


@dataclass(frozen=True, slots=True)
class ScoredHit:
    posting: JobPosting
    matched_title: str
    location_phrase: str
    score: float
    reason: str
    closest_chunk_label: str


def normalize_title_text(value: str) -> str:
    text_value = value.casefold()
    text_value = re.sub(r"[^\w\s/+&-]", " ", text_value)
    return " ".join(text_value.split())


def title_tokens(value: str, *, strip_seniority: bool = False) -> list[str]:
    tokens = normalize_title_text(value).split()
    out: list[str] = []
    for tok in tokens:
        if strip_seniority and tok in _SENIORITY_TOKENS:
            continue
        if tok in _STOP_TOKENS:
            continue
        out.append(tok)
    return out


def title_matches(confirmed: str, posting_title: str) -> bool:
    """Confirmed title is a contiguous phrase, token subset, or close role family.

    Role-family: the last two significant tokens of the confirmed title appear
    contiguously in the posting (e.g. "Digital Marketing Specialist" ↔
    "Content Marketing Specialist").
    """
    conf_norm = normalize_title_text(confirmed)
    post_norm = normalize_title_text(posting_title)
    if not conf_norm or not post_norm:
        return False

    conf_stripped = " ".join(title_tokens(confirmed, strip_seniority=True))
    post_stripped = " ".join(title_tokens(posting_title, strip_seniority=True))
    if conf_stripped and conf_stripped in post_stripped:
        return True

    conf_tokens = [
        t for t in title_tokens(confirmed, strip_seniority=True) if len(t) > 2
    ]
    if not conf_tokens:
        # Very short titles (e.g. "QA") — require contiguous after strip.
        return conf_stripped != "" and conf_stripped in post_stripped

    post_token_set = set(title_tokens(posting_title, strip_seniority=True))
    if all(t in post_token_set for t in conf_tokens):
        return True

    # Soft family match: last two tokens as a contiguous phrase in the posting.
    if len(conf_tokens) >= 2:
        tail = " ".join(conf_tokens[-2:])
        if tail and tail in post_stripped:
            return True

    # Soft domain match: shared stem (e.g. marketing) + both look like role titles.
    # Use unstripped tokens so "manager" / "director" still count as role suffixes
    # (they are also seniority tokens and would otherwise be stripped).
    conf_raw = set(title_tokens(confirmed, strip_seniority=False))
    post_raw = set(title_tokens(posting_title, strip_seniority=False))
    # Do not soft-match marketing/social prefs onto eng titles ("…, Growth").
    eng = frozenset({"engineer", "developer", "engineering"})
    if post_raw & eng and not (conf_raw & eng):
        return False
    shared_stem = bool(conf_raw & post_raw & _DOMAIN_STEMS)
    if not shared_stem:
        for group in _RELATED_STEM_GROUPS:
            if conf_raw & group and post_raw & group:
                shared_stem = True
                break
    return bool(shared_stem and conf_raw & _ROLE_SUFFIXES and post_raw & _ROLE_SUFFIXES)


def posting_seniority_tokens(posting_title: str) -> set[str]:
    return {
        t for t in normalize_title_text(posting_title).split() if t in _SENIORITY_TOKENS
    }


def seniority_allows(bands: list[str], posting_title: str) -> tuple[bool, bool]:
    """Return (allowed, explicit_band_match). No token → allowed, not explicit."""
    tokens = posting_seniority_tokens(posting_title)
    title_words = set(normalize_title_text(posting_title).split())
    if not tokens:
        return True, False

    band_set = set(bands)
    user_has_junior = bool(band_set & {"intern", "junior"})
    user_has_senior = bool(band_set & {"senior", "staff_principal", "lead_manager"})
    user_is_ic_only = bool(band_set) and band_set.isdisjoint(_MANAGER_BANDS)
    user_is_manager_only = bool(band_set) and band_set <= _MANAGER_BANDS

    # Drop clear contradictions (plan).
    if (
        tokens & _JUNIORISH
        and user_has_senior
        and not user_has_junior
        and not (band_set & {"intern", "junior", "mid"})
    ):
        return False, False
    if tokens & _SENIORISH and band_set and band_set <= {"intern", "junior"}:
        return False, False
    # IC-only users: drop exec / Engineering Manager style titles, but keep
    # "… Marketing Manager" / "Program Manager" etc.
    if user_is_ic_only:
        if tokens & _MANAGERISH:
            return False, False
        if "manager" in tokens and title_words & _PEOPLE_MANAGER_TITLE:
            return False, False
    if (
        user_is_manager_only
        and tokens & _JUNIORISH
        and not (tokens & (_MANAGERISH | {"manager"}))
    ):
        return False, False

    explicit = any(tokens & _BAND_TOKENS.get(band, frozenset()) for band in bands)
    return True, explicit


def location_allows(
    prefs: MatchPreference,
    *,
    remote: bool | None,
    countries: list[str] | None,
    parse_status: str | None,
) -> tuple[bool, str]:
    """Apply remote_only / remote_ok / onsite_only. Failed parse → excluded.

    Remote postings are eligible for remote_only / remote_ok even when the ATS
    country does not overlap the user's countries (seed boards rarely tag
    Ireland-eligible remote). Country still filters onsite / hybrid rows.
    """
    if parse_status == "failed" or parse_status is None:
        return False, "location unavailable"

    pref_codes = {
        c
        for label in (prefs.countries or [])
        if (c := country_code_for(label)) is not None
    }
    posting_codes = set(countries or [])
    is_remote = bool(remote)
    remote_pref = prefs.remote_preference

    def country_overlap() -> bool:
        if not pref_codes:
            # No country filter from the user.
            return True
        return bool(pref_codes & posting_codes)

    if remote_pref == "remote_only":
        if not is_remote:
            return False, "not remote"
        # Any remote role — country tags on ATS boards are often hiring hubs,
        # not work-authorization lists.
        return True, "remote" + (
            f" · {', '.join(sorted(pref_codes & posting_codes))}"
            if pref_codes and posting_codes and country_overlap()
            else ""
        )

    if remote_pref == "onsite_only":
        # Pure remote with no overlapping country is not onsite.
        if is_remote and (not posting_codes or not country_overlap()):
            return False, "remote-only role"
        if pref_codes and not country_overlap():
            return False, "country mismatch"
        phrase = (
            ", ".join(sorted(posting_codes & pref_codes))
            if pref_codes
            else (", ".join(sorted(posting_codes)) if posting_codes else "onsite")
        )
        return True, phrase or "onsite"

    # remote_ok (Hybrid in UI): any remote role, or onsite with country overlap.
    if is_remote:
        return True, "remote" + (
            f" · {', '.join(sorted(pref_codes & posting_codes))}"
            if pref_codes and posting_codes and country_overlap()
            else ""
        )

    if pref_codes:
        if country_overlap():
            return True, ", ".join(sorted(pref_codes & posting_codes))
        return False, "country mismatch"

    # No countries set: any parsed location is fine.
    if posting_codes:
        return True, ", ".join(sorted(posting_codes))
    return True, "location ok"


def ensure_location_normalized(session: Session, posting: JobPosting) -> JobPosting:
    """Fill location_* when missing; do not flip a prior ok → failed on same raw."""
    raw = posting.location_raw or ""
    if (
        posting.location_parse_status in {"ok", "partial", "failed"}
        and posting.location_remote is not None
    ):
        return posting

    parsed = normalize_location(raw)
    posting.location_remote = parsed.remote
    posting.location_countries = parsed.countries
    posting.location_parse_status = parsed.status
    session.add(posting)
    return posting


def apply_location_to_posting(posting: JobPosting, *, force: bool = False) -> None:
    """Set location fields from ``location_raw`` (ingest / backfill)."""
    raw = posting.location_raw or ""
    # Idempotent: if status already ok/partial/failed for this raw, keep it
    # unless fields were never written — or caller forces a re-parse.
    if (
        not force
        and posting.location_parse_status in {"ok", "partial", "failed"}
        and posting.location_remote is not None
    ):
        return
    parsed = normalize_location(raw)
    posting.location_remote = parsed.remote
    posting.location_countries = parsed.countries
    posting.location_parse_status = parsed.status


def lookback_cutoff(
    *,
    now: datetime | None = None,
    hours: int = DEFAULT_LOOKBACK_HOURS,
) -> datetime:
    when = now or datetime.now(UTC)
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return when - timedelta(hours=hours)


def _title_prefilter_clause(titles: list[str]) -> ColumnElement[bool] | None:
    """SQL superset of ``title_matches`` — phrase / tail / soft domain+role.

    Python still applies the exact matcher; this only shrinks the candidate set
    so Pass 1 does not load the full active catalog into memory.
    """
    clauses: list[ColumnElement[bool]] = []
    title_col = col(JobPosting.title)
    for confirmed in titles:
        stripped = title_tokens(confirmed, strip_seniority=True)
        if stripped:
            phrase = " ".join(stripped)
            clauses.append(title_col.ilike(f"%{phrase}%"))
            if len(stripped) >= 2:
                clauses.append(title_col.ilike(f"%{' '.join(stripped[-2:])}%"))
        conf_raw = set(title_tokens(confirmed, strip_seniority=False))
        stems = set(conf_raw & _DOMAIN_STEMS)
        for group in _RELATED_STEM_GROUPS:
            if conf_raw & group:
                stems |= set(group)
        if stems:
            stem_or = or_(*[title_col.ilike(f"%{stem}%") for stem in stems])
            suffix_or = or_(
                *[title_col.ilike(f"%{suffix}%") for suffix in _ROLE_SUFFIXES]
            )
            clauses.append(and_(stem_or, suffix_or))
    if not clauses:
        return None
    return or_(*clauses)


def filter_eligible(
    session: Session,
    prefs: MatchPreference,
    *,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    now: datetime | None = None,
) -> list[EligibleHit]:
    """Pass 1 — confirmed targets only. No embeddings."""
    titles = list(prefs.titles or [])
    if not titles:
        return []

    cutoff = lookback_cutoff(now=now, hours=lookback_hours)
    # Approximate lookback (plan): vendor stamp when present, else last_seen_at.
    # greatest() so a fresh ingest still surfaces boards whose ATS updated_at
    # lags (Greenhouse often exposes edit time, not first published).
    freshness = sa_func.greatest(
        col(JobPosting.vendor_updated_at),
        col(JobPosting.vendor_posted_at),
        col(JobPosting.last_seen_at),
    )
    where_clauses: list[ColumnElement[bool]] = [
        JobPosting.is_active.is_(True),  # type: ignore[arg-type]
        freshness >= cutoff,
        col(JobPosting.description_text).is_not(None),
    ]
    title_clause = _title_prefilter_clause(titles)
    if title_clause is not None:
        where_clauses.append(title_clause)

    # Skip multi-MB description + vectors until Pass 2 / response shaping.
    # SQLModel Field props confuse pyrefly's defer() attribute typing.
    rows = list(
        session.exec(
            select(JobPosting)
            .options(
                # pyrefly: ignore[bad-argument-type]
                defer(JobPosting.embedding),
                # pyrefly: ignore[bad-argument-type]
                defer(JobPosting.description_text),
            )
            .where(*where_clauses)
        ).all()
    )

    bands = list(prefs.seniority_bands or [])
    hits: list[EligibleHit] = []
    dirty = False

    for row in rows:
        before_status = row.location_parse_status
        ensure_location_normalized(session, row)
        if row.location_parse_status != before_status:
            dirty = True

        matched: str | None = None
        for title in titles:
            if title_matches(title, row.title or ""):
                matched = title
                break
        if matched is None:
            continue

        ok_sen, explicit = seniority_allows(bands, row.title or "")
        if not ok_sen:
            continue

        ok_loc, loc_phrase = location_allows(
            prefs,
            remote=row.location_remote,
            countries=list(row.location_countries or []),
            parse_status=row.location_parse_status,
        )
        if not ok_loc:
            continue

        hits.append(
            EligibleHit(
                posting=row,
                matched_title=matched,
                location_phrase=loc_phrase,
                seniority_explicit=explicit,
            )
        )

    if dirty:
        session.commit()
    return hits


def embedding_input(title: str, description: str) -> str:
    excerpt = (description or "").strip()[:_EMBED_EXCERPT_CHARS]
    return f"{(title or '').strip()}\n\n{excerpt}".strip()


def ensure_posting_embedding(
    session: Session,
    posting: JobPosting,
    embeddings: EmbeddingsClient | None = None,
) -> bool:
    """Embed title + description excerpt once. Returns True if a vector is present."""
    if posting.embedding is not None:
        return True
    if not posting.description_text:
        return False
    client = embeddings or get_embeddings_client()
    if not client.configured():
        return False
    vector = client.embed_query(
        embedding_input(posting.title or "", posting.description_text)
    )
    posting.embedding = vector
    posting.updated_at = datetime.now(UTC)
    session.add(posting)
    session.commit()
    return True


def _chunk_label(chunk_type: str) -> str:
    kind = (chunk_type or "").casefold()
    if kind.startswith("experience"):
        return "experience"
    if kind.startswith("project"):
        return "project"
    if kind == "skills":
        return "skills"
    if kind in {"summary", "basics", "education"}:
        return kind
    return kind or "profile"


def _weak_scored_hit(hit: EligibleHit) -> ScoredHit:
    return ScoredHit(
        posting=hit.posting,
        matched_title=hit.matched_title,
        location_phrase=hit.location_phrase,
        score=0.01 if hit.seniority_explicit else 0.0,
        reason=_reason_template(hit.matched_title, hit.location_phrase, "profile"),
        closest_chunk_label="profile",
    )


def _postings_with_embedding(
    session: Session,
    posting_ids: list[UUID],
) -> set[UUID]:
    """Ids among ``posting_ids`` that already have a stored vector."""
    if not posting_ids:
        return set()
    rows = session.exec(
        select(JobPosting.id).where(
            col(JobPosting.id).in_(posting_ids),
            col(JobPosting.embedding).is_not(None),
        )
    ).all()
    return set(rows)


def _batch_cosine_scores(
    session: Session,
    user_id: UUID,
    posting_ids: list[UUID],
) -> dict[UUID, tuple[float, str]]:
    """One round-trip: best (1 − cosine distance) + closest chunk label per posting."""
    if not posting_ids:
        return {}
    stmt = text(
        """
        SELECT
            jp.id AS posting_id,
            MIN(pc.embedding <=> jp.embedding) AS dist,
            (ARRAY_AGG(pc.chunk_type ORDER BY pc.embedding <=> jp.embedding))[1]
                AS chunk_type
        FROM job_posting AS jp
        CROSS JOIN profile_chunk AS pc
        WHERE pc.user_id = :user_id
          AND jp.id IN :ids
          AND jp.embedding IS NOT NULL
          AND pc.embedding IS NOT NULL
        GROUP BY jp.id
        """
    ).bindparams(bindparam("ids", expanding=True))
    result = session.execute(
        stmt,
        {"user_id": user_id, "ids": list(posting_ids)},
    )
    out: dict[UUID, tuple[float, str]] = {}
    for row in result:
        posting_id = row.posting_id if hasattr(row, "posting_id") else row[0]
        dist_val = row.dist if hasattr(row, "dist") else row[1]
        chunk_type = row.chunk_type if hasattr(row, "chunk_type") else row[2]
        if isinstance(posting_id, str):
            posting_id = UUID(posting_id)
        score = 1.0 - float(dist_val if dist_val is not None else 1.0)
        out[posting_id] = (score, _chunk_label(str(chunk_type or "profile")))
    return out


def score_eligible(
    session: Session,
    user_id: UUID,
    hits: list[EligibleHit],
    *,
    embeddings: EmbeddingsClient | None = None,
    max_request_embeds: int = MAX_REQUEST_PATH_EMBEDS,
    max_vector_candidates: int = MAX_VECTOR_SCORE_CANDIDATES,
) -> list[ScoredHit]:
    """Pass 2 — max cosine vs profile chunks.

    Scores already-embedded hits in one SQL batch (capped). At most
    ``max_request_embeds`` on-demand API embeds run on the request path; the
    rest get a weak Pass-1 score so Jobs For You stays interactive.
    """
    if not hits:
        return []

    client = embeddings or get_embeddings_client()
    has_chunks = (
        session.exec(
            select(ProfileChunk.id).where(ProfileChunk.user_id == user_id).limit(1)
        ).first()
        is not None
    )
    if not has_chunks:
        return [_weak_scored_hit(hit) for hit in hits]

    by_id = {hit.posting.id: hit for hit in hits}
    embedded_ids = _postings_with_embedding(session, list(by_id.keys()))
    with_vec = [by_id[pid] for pid in embedded_ids if pid in by_id]
    without_vec = [hit for hit in hits if hit.posting.id not in embedded_ids]
    with_vec.sort(key=lambda h: _vendor_sort_key(h.posting), reverse=True)
    without_vec.sort(key=lambda h: _vendor_sort_key(h.posting), reverse=True)

    vector_hits = with_vec[: max(0, max_vector_candidates)]
    overflow_hits = with_vec[max(0, max_vector_candidates) :]

    scores = _batch_cosine_scores(
        session,
        user_id,
        [hit.posting.id for hit in vector_hits],
    )

    out: list[ScoredHit] = []
    for hit in vector_hits:
        packed = scores.get(hit.posting.id)
        if packed is None:
            out.append(_weak_scored_hit(hit))
            continue
        base, label = packed
        adj = base + (0.001 if hit.seniority_explicit else 0.0)
        out.append(
            ScoredHit(
                posting=hit.posting,
                matched_title=hit.matched_title,
                location_phrase=hit.location_phrase,
                score=adj,
                reason=_reason_template(hit.matched_title, hit.location_phrase, label),
                closest_chunk_label=label,
            )
        )

    for hit in overflow_hits:
        out.append(_weak_scored_hit(hit))

    embeds_used = 0
    for hit in without_vec:
        if embeds_used >= max(0, max_request_embeds):
            out.append(_weak_scored_hit(hit))
            continue
        session.refresh(hit.posting, attribute_names=["description_text", "embedding"])
        if not ensure_posting_embedding(session, hit.posting, client):
            out.append(_weak_scored_hit(hit))
            continue
        embeds_used += 1
        packed = _batch_cosine_scores(session, user_id, [hit.posting.id]).get(
            hit.posting.id
        )
        if packed is None:
            out.append(_weak_scored_hit(hit))
            continue
        base, label = packed
        adj = base + (0.001 if hit.seniority_explicit else 0.0)
        out.append(
            ScoredHit(
                posting=hit.posting,
                matched_title=hit.matched_title,
                location_phrase=hit.location_phrase,
                score=adj,
                reason=_reason_template(hit.matched_title, hit.location_phrase, label),
                closest_chunk_label=label,
            )
        )

    return out


def _reason_template(matched_title: str, location_phrase: str, chunk_label: str) -> str:
    return (
        f"Matched “{matched_title}” · {location_phrase} · closest to your {chunk_label}"
    )


def _vendor_sort_key(posting: JobPosting) -> datetime:
    for value in (
        posting.vendor_updated_at,
        posting.vendor_posted_at,
        posting.last_seen_at,
    ):
        if value is not None:
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value
    return datetime.min.replace(tzinfo=UTC)


def upsert_ledger(
    session: Session,
    *,
    user_id: UUID,
    posting_id: UUID,
    score: float,
    reason: str,
    matched_title: str | None,
    commit: bool = True,
) -> MatchLedger:
    row = session.exec(
        select(MatchLedger).where(
            MatchLedger.user_id == user_id,
            MatchLedger.posting_id == posting_id,
        )
    ).first()
    now = datetime.now(UTC)
    if row is None:
        row = MatchLedger(
            id=uuid4(),
            user_id=user_id,
            posting_id=posting_id,
            score=score,
            reason=reason,
            matched_title=matched_title,
            created_at=now,
            updated_at=now,
        )
    else:
        row.score = score
        row.reason = reason
        row.matched_title = matched_title
        row.updated_at = now
    session.add(row)
    if commit:
        session.commit()
        session.refresh(row)
    return row


def mark_opened(
    session: Session,
    *,
    user_id: UUID,
    posting_id: UUID,
) -> MatchLedger | None:
    row = session.exec(
        select(MatchLedger).where(
            MatchLedger.user_id == user_id,
            MatchLedger.posting_id == posting_id,
        )
    ).first()
    now = datetime.now(UTC)
    if row is None:
        # Opening before a shortlist pass — still record it.
        posting = session.get(JobPosting, posting_id)
        if posting is None:
            return None
        row = MatchLedger(
            id=uuid4(),
            user_id=user_id,
            posting_id=posting_id,
            score=None,
            reason="",
            matched_title=None,
            opened_at=now,
            created_at=now,
            updated_at=now,
        )
    else:
        if row.opened_at is None:
            row.opened_at = now
        row.updated_at = now
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def shortlist_for_user(
    session: Session,
    prefs: MatchPreference,
    *,
    user_id: UUID,
    cap: int = DEFAULT_SHORTLIST_CAP,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    settings: Settings | None = None,
    embeddings: EmbeddingsClient | None = None,
) -> list[ScoredHit]:
    """Filter → score → omit opened → rank → cap. Upserts match ledger rows."""
    _ = settings or get_settings()
    eligible = filter_eligible(session, prefs, lookback_hours=lookback_hours)
    scored = score_eligible(session, user_id, eligible, embeddings=embeddings)

    opened_ids = {
        row.posting_id
        for row in session.exec(
            select(MatchLedger).where(
                MatchLedger.user_id == user_id,
                col(MatchLedger.opened_at).is_not(None),
            )
        ).all()
    }
    fresh = [h for h in scored if h.posting.id not in opened_ids]
    fresh.sort(
        key=lambda h: (-h.score, _vendor_sort_key(h.posting)),
    )
    top = fresh[: max(1, cap)] if fresh else []

    for hit in top:
        # Descriptions were deferred in Pass 1 — load only for the capped rows.
        if hit.posting.description_text is None:
            session.refresh(hit.posting, attribute_names=["description_text"])
        upsert_ledger(
            session,
            user_id=user_id,
            posting_id=hit.posting.id,
            score=hit.score,
            reason=hit.reason,
            matched_title=hit.matched_title,
            commit=False,
        )
    if top:
        session.commit()
    return top


def backfill_locations(
    session: Session,
    *,
    limit: int | None = None,
    force: bool = False,
) -> int:
    """Normalize location_* for rows that still lack a parse status.

    With ``force=True``, re-parse every row (or up to ``limit``) so improved
    city→country rules can heal prior ``failed`` / ``partial`` results.
    """
    if force:
        stmt = select(JobPosting).order_by(col(JobPosting.last_seen_at).desc())
    else:
        stmt = select(JobPosting).where(col(JobPosting.location_parse_status).is_(None))
    if limit is not None:
        stmt = stmt.limit(limit)
    rows = list(session.exec(stmt).all())
    for row in rows:
        apply_location_to_posting(row, force=force)
        session.add(row)
    session.commit()
    return len(rows)


def backfill_embeddings(
    session: Session,
    *,
    limit: int | None = None,
    embeddings: EmbeddingsClient | None = None,
) -> int:
    """Embed active postings that have description_text but no vector."""
    client = embeddings or get_embeddings_client()
    if not client.configured():
        return 0
    stmt = (
        select(JobPosting)
        .where(
            JobPosting.is_active.is_(True),  # type: ignore[union-attr]
            col(JobPosting.description_text).is_not(None),
            col(JobPosting.embedding).is_(None),
        )
        .order_by(col(JobPosting.last_seen_at).desc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    rows = list(session.exec(stmt).all())
    done = 0
    for row in rows:
        if ensure_posting_embedding(session, row, client):
            done += 1
    return done
