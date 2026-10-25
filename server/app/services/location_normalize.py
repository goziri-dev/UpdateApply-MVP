"""Normalize ATS location strings into remote + country codes (Phase 2).

Pure functions — ``location_raw`` is never mutated. Fail closed when neither
remote nor a country can be inferred (``location_parse_status = failed``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ISO-3166-1 alpha-2. Keys are casefolded aliases (names, demonyms, common typos).
_COUNTRY_ALIASES: dict[str, str] = {
    "us": "US",
    "usa": "US",
    "u.s.": "US",
    "u.s.a.": "US",
    "united states": "US",
    "united states of america": "US",
    "america": "US",
    "uk": "GB",
    "u.k.": "GB",
    "gb": "GB",
    "great britain": "GB",
    "united kingdom": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",
    "ie": "IE",
    "ireland": "IE",
    "republic of ireland": "IE",
    "ng": "NG",
    "nigeria": "NG",
    "ca": "CA",
    "canada": "CA",
    "de": "DE",
    "germany": "DE",
    "fr": "FR",
    "france": "FR",
    "nl": "NL",
    "netherlands": "NL",
    "the netherlands": "NL",
    "holland": "NL",
    "au": "AU",
    "australia": "AU",
    "in": "IN",
    "india": "IN",
    "sg": "SG",
    "singapore": "SG",
    "jp": "JP",
    "japan": "JP",
    "br": "BR",
    "brazil": "BR",
    "mx": "MX",
    "mexico": "MX",
    "es": "ES",
    "spain": "ES",
    "pt": "PT",
    "portugal": "PT",
    "it": "IT",
    "italy": "IT",
    "se": "SE",
    "sweden": "SE",
    "no": "NO",
    "norway": "NO",
    "dk": "DK",
    "denmark": "DK",
    "fi": "FI",
    "finland": "FI",
    "ch": "CH",
    "switzerland": "CH",
    "at": "AT",
    "austria": "AT",
    "be": "BE",
    "belgium": "BE",
    "pl": "PL",
    "poland": "PL",
    "za": "ZA",
    "south africa": "ZA",
    "ke": "KE",
    "kenya": "KE",
    "gh": "GH",
    "ghana": "GH",
    "ae": "AE",
    "uae": "AE",
    "united arab emirates": "AE",
    "il": "IL",
    "israel": "IL",
    "nz": "NZ",
    "new zealand": "NZ",
    "kr": "KR",
    "south korea": "KR",
    "korea": "KR",
    "cn": "CN",
    "china": "CN",
    "hk": "HK",
    "hong kong": "HK",
    "tw": "TW",
    "taiwan": "TW",
    "ph": "PH",
    "philippines": "PH",
    "my": "MY",
    "malaysia": "MY",
    "id": "ID",
    "indonesia": "ID",
    "ar": "AR",
    "argentina": "AR",
    "cl": "CL",
    "chile": "CL",
    "co": "CO",
    "colombia": "CO",
}

_REMOTE_RE = re.compile(
    r"\b(remote|work\s*from\s*home|wfh|distributed|anywhere)\b",
    re.IGNORECASE,
)
# Split multi-location blobs ("New York, NY / London, UK", "US or UK").
_SPLIT_RE = re.compile(r"[|/;]|\bor\b|\band\b", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z.'\s-]*")

# Well-known city / metro → country when ATS omits the country name.
# Longer keys win (same sort as aliases). Casefolded.
_CITY_COUNTRY: dict[str, str] = {
    "san francisco bay area": "US",
    "san francisco": "US",
    "sf bay area": "US",
    "bay area": "US",
    "new york city": "US",
    "new york": "US",
    "nyc": "US",
    "washington d.c.": "US",
    "washington dc": "US",
    "washington d c": "US",
    "los angeles": "US",
    "seattle": "US",
    "austin": "US",
    "chicago": "US",
    "boston": "US",
    "denver": "US",
    "atlanta": "US",
    "miami": "US",
    "toronto": "CA",
    "vancouver": "CA",
    "montreal": "CA",
    "london": "GB",
    "manchester": "GB",
    "edinburgh": "GB",
    "dublin": "IE",
    "paris": "FR",
    "lyon": "FR",
    "berlin": "DE",
    "munich": "DE",
    "amsterdam": "NL",
    "warsaw": "PL",
    "krakow": "PL",
    "cracow": "PL",
    "lisbon": "PT",
    "madrid": "ES",
    "barcelona": "ES",
    "stockholm": "SE",
    "copenhagen": "DK",
    "oslo": "NO",
    "helsinki": "FI",
    "zurich": "CH",
    "sydney": "AU",
    "melbourne": "AU",
    "singapore": "SG",
    "tokyo": "JP",
    "bangalore": "IN",
    "bengaluru": "IN",
    "mumbai": "IN",
    "hyderabad": "IN",
    "lagos": "NG",
    "abuja": "NG",
}


@dataclass(frozen=True, slots=True)
class LocationParseResult:
    remote: bool
    countries: list[str]  # ISO-3166-1 alpha-2, unique, sorted
    status: str  # ok | partial | failed
    city: str | None = None


def country_code_for(label: str) -> str | None:
    """Map a free-text country preference to an ISO code, if known."""
    key = " ".join(label.split()).strip().casefold()
    if not key:
        return None
    if len(key) == 2 and key.isalpha():
        return key.upper()
    return _COUNTRY_ALIASES.get(key)


def normalize_location(raw: str | None) -> LocationParseResult:
    """Parse ``location_raw`` into remote + countries. Never mutates the raw."""
    text = " ".join((raw or "").split()).strip()
    if not text:
        return LocationParseResult(remote=False, countries=[], status="failed")

    remote = bool(_REMOTE_RE.search(text))
    countries = _extract_countries(text)
    if not countries:
        countries = _countries_from_cities(text)
    city = _guess_city(text, countries)

    # Country found → ok. Remote with no country → partial (fail-closed when the
    # user set countries). Neither → failed (never guess a country).
    if countries:
        status = "ok"
    elif remote:
        status = "partial"
    else:
        status = "failed"

    return LocationParseResult(
        remote=remote,
        countries=countries,
        status=status,
        city=city,
    )


def _extract_countries(text: str) -> list[str]:
    found: set[str] = set()
    # Prefer longer aliases first so "united states" wins over "us" inside it.
    aliases = sorted(_COUNTRY_ALIASES.items(), key=lambda kv: len(kv[0]), reverse=True)
    folded = text.casefold()
    for alias, code in aliases:
        # Word-ish boundary so "in" (India) does not match inside "engineering".
        pattern = re.compile(
            rf"(?<![a-z]){re.escape(alias)}(?![a-z])",
            re.IGNORECASE,
        )
        if pattern.search(folded):
            found.add(code)

    # Bare 2-letter tokens after commas / dashes ("Remote - US", "London, UK").
    known_codes = set(_COUNTRY_ALIASES.values())
    for part in _SPLIT_RE.split(text) + re.split(r"[,–—-]", text):
        token = part.strip().casefold()
        if len(token) == 2 and token.isalpha() and token.upper() in known_codes:
            found.add(token.upper())
        mapped = _COUNTRY_ALIASES.get(token)
        if mapped:
            found.add(mapped)

    return sorted(found)


def _countries_from_cities(text: str) -> list[str]:
    """Infer country from well-known cities when ATS omits the country label."""
    found: set[str] = set()
    folded = text.casefold()
    cities = sorted(_CITY_COUNTRY.items(), key=lambda kv: len(kv[0]), reverse=True)
    for city, code in cities:
        pattern = re.compile(
            rf"(?<![a-z]){re.escape(city)}(?![a-z])",
            re.IGNORECASE,
        )
        if pattern.search(folded):
            found.add(code)
    return sorted(found)


def _guess_city(text: str, countries: list[str]) -> str | None:
    """Best-effort city label for boosts — not used as a hard filter."""
    # Strip remote and country phrases, take the first remaining place-ish token.
    cleaned = _REMOTE_RE.sub(" ", text)
    for code in countries:
        for alias, c in _COUNTRY_ALIASES.items():
            if c == code:
                cleaned = re.sub(
                    rf"(?<![a-z]){re.escape(alias)}(?![a-z])",
                    " ",
                    cleaned,
                    flags=re.IGNORECASE,
                )
        cleaned = re.sub(
            rf"(?<![a-z]){re.escape(code)}(?![a-z])",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )
    cleaned = re.sub(r"[,/|–—\-()]+", " ", cleaned)
    cleaned = " ".join(cleaned.split()).strip()
    if not cleaned:
        return None
    # First comma-free chunk, title-cased lightly.
    match = _TOKEN_RE.match(cleaned)
    if match is None:
        return None
    city = match.group(0).strip(" .'-")
    if len(city) < 2:
        return None
    # Avoid treating lone region codes as cities.
    if city.casefold() in _COUNTRY_ALIASES or (len(city) == 2 and city.isalpha()):
        return None
    return city
