"""Resume basics / contact-header helpers shared by map, remake, and render."""

from __future__ import annotations

from typing import Any

from app.schemas.resume import ResumeBasics

# Scalar contact/header fields that must survive parse → remake → tailor → PDF.
_BASICS_SCALAR_FIELDS = (
    "name",
    "email",
    "phone",
    "location",
    "citizenship",
    "availability",
)


def _string_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()]


def basics_from_raw(basics_raw: dict[str, Any] | None) -> ResumeBasics:
    """Coerce a profile/resume basics dict into typed ResumeBasics."""
    raw = basics_raw if isinstance(basics_raw, dict) else {}
    return ResumeBasics(
        name=str(raw.get("name") or ""),
        email=str(raw.get("email") or ""),
        phone=str(raw.get("phone") or ""),
        location=str(raw.get("location") or ""),
        citizenship=str(raw.get("citizenship") or ""),
        availability=str(raw.get("availability") or ""),
        languages=_string_list(raw.get("languages")),
        links=_string_list(raw.get("links")),
    )


def basics_to_profile_dict(basics: ResumeBasics | dict[str, Any]) -> dict[str, Any]:
    """Normalize basics for persisted profile JSON."""
    if isinstance(basics, ResumeBasics):
        data = basics.model_dump()
    else:
        data = dict(basics)
    return {
        "name": str(data.get("name") or ""),
        "email": str(data.get("email") or ""),
        "phone": str(data.get("phone") or ""),
        "location": str(data.get("location") or ""),
        "citizenship": str(data.get("citizenship") or ""),
        "availability": str(data.get("availability") or ""),
        "languages": _string_list(data.get("languages")),
        "links": _string_list(data.get("links")),
    }


def fill_missing_basics_contact(
    primary: dict[str, Any] | ResumeBasics | None,
    fallback: dict[str, Any] | ResumeBasics | None,
) -> ResumeBasics:
    """Prefer ``primary`` contact values; fill empties from ``fallback``.

    Used after remake so parse-time phone/citizenship/etc. are not dropped
    when the rewriter omits them.
    """
    primary_b = (
        primary
        if isinstance(primary, ResumeBasics)
        else basics_from_raw(primary if isinstance(primary, dict) else None)
    )
    fallback_b = (
        fallback
        if isinstance(fallback, ResumeBasics)
        else basics_from_raw(fallback if isinstance(fallback, dict) else None)
    )
    merged = basics_to_profile_dict(primary_b)
    fallback_d = basics_to_profile_dict(fallback_b)
    for key in _BASICS_SCALAR_FIELDS:
        if not str(merged.get(key) or "").strip():
            merged[key] = fallback_d.get(key) or ""
    if not merged.get("languages"):
        merged["languages"] = list(fallback_d.get("languages") or [])
    if not merged.get("links"):
        merged["links"] = list(fallback_d.get("links") or [])
    return basics_from_raw(merged)
