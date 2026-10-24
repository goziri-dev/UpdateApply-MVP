"""Per-item deepen novelty store under profile ``_deepen``.

Choice (documented): persist asked questions / themes on the profile JSONB
row under ``_deepen.by_item[<item_id>]``, not only process-local sessions.
That way later deepen runs stay novel after server restarts and across
devices once the profile is loaded.

Also pulls prior onboarding questions from ``_onboarding.item_transcripts``
and ``_onboarding.item_scripts`` for the same item id.
"""

from __future__ import annotations

import time
from copy import deepcopy
from typing import Any, Literal

# Cap stored strings so meta stays small.
_MAX_ASKED = 64
_MAX_THEMES = 32
_MAX_QUESTION_LEN = 400


def collect_prior_for_item(
    profile_data: dict[str, Any], item_id: str
) -> dict[str, Any]:
    """Return prior questions + themes for novelty exclusion.

    Sources:
    - ``_deepen.by_item[item_id].asked_questions`` / ``themes``
    - ``_onboarding.item_transcripts[item_id]`` question fields
    - ``_onboarding.item_scripts[item_id].questions`` / ``coverage``
    """
    iid = (item_id or "").strip()
    asked: list[str] = []
    themes: list[str] = []
    seen_q: set[str] = set()
    seen_t: set[str] = set()

    def _add_q(raw: object) -> None:
        text = str(raw or "").strip()
        if not text:
            return
        key = text.casefold()
        if key in seen_q:
            return
        seen_q.add(key)
        asked.append(text[:_MAX_QUESTION_LEN])

    def _add_t(raw: object) -> None:
        text = str(raw or "").strip()
        if not text:
            return
        key = text.casefold()
        if key in seen_t:
            return
        seen_t.add(key)
        themes.append(text[:120])

    deepen = profile_data.get("_deepen")
    if isinstance(deepen, dict):
        by_item = deepen.get("by_item")
        if isinstance(by_item, dict):
            entry = by_item.get(iid)
            if isinstance(entry, dict):
                for q in entry.get("asked_questions") or []:
                    _add_q(q)
                for t in entry.get("themes") or []:
                    _add_t(t)

    onboarding = profile_data.get("_onboarding")
    if isinstance(onboarding, dict):
        transcripts = onboarding.get("item_transcripts")
        if isinstance(transcripts, dict):
            for turn in transcripts.get(iid) or []:
                if isinstance(turn, dict):
                    _add_q(turn.get("question"))
        scripts = onboarding.get("item_scripts")
        if isinstance(scripts, dict):
            script = scripts.get(iid)
            if isinstance(script, dict):
                for q in script.get("questions") or []:
                    _add_q(q)
                for c in script.get("coverage") or []:
                    _add_t(c)

    return {
        "asked_questions": asked[:_MAX_ASKED],
        "themes": themes[:_MAX_THEMES],
    }


def record_deepen_session(
    profile_data: dict[str, Any],
    *,
    item_id: str,
    mode: Literal["guided", "journal"],
    questions: list[str],
    themes: list[str] | None = None,
    transcripts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Merge this deepen run into ``_deepen.by_item[item_id]`` (idempotent append)."""
    iid = (item_id or "").strip()
    if not iid:
        return profile_data

    out = deepcopy(profile_data)
    meta = dict(out.get("_deepen") or {})
    by_item = dict(meta.get("by_item") or {})
    entry = dict(by_item.get(iid) or {})

    prior_qs = [
        str(q).strip() for q in (entry.get("asked_questions") or []) if str(q).strip()
    ]
    prior_themes = [
        str(t).strip() for t in (entry.get("themes") or []) if str(t).strip()
    ]
    seen_q = {q.casefold() for q in prior_qs}
    seen_t = {t.casefold() for t in prior_themes}

    for q in questions:
        text = str(q or "").strip()[:_MAX_QUESTION_LEN]
        if not text or text.casefold() in seen_q:
            continue
        seen_q.add(text.casefold())
        prior_qs.append(text)

    for t in themes or []:
        text = str(t or "").strip()[:120]
        if not text or text.casefold() in seen_t:
            continue
        seen_t.add(text.casefold())
        prior_themes.append(text)

    if mode == "journal" and "Journal update" not in prior_themes:
        prior_themes.append("Journal update")

    sessions = list(entry.get("sessions") or [])
    # Keep last few session stubs for debugging; not required for novelty.
    sessions.append(
        {
            "mode": mode,
            "at": time.time(),
            "question_count": len([q for q in questions if str(q).strip()]),
            "answer_count": len(
                [
                    t
                    for t in (transcripts or [])
                    if isinstance(t, dict) and str(t.get("answer") or "").strip()
                ]
            ),
        }
    )
    sessions = sessions[-8:]

    entry["asked_questions"] = prior_qs[-_MAX_ASKED:]
    entry["themes"] = prior_themes[-_MAX_THEMES:]
    entry["sessions"] = sessions
    by_item[iid] = entry
    meta["by_item"] = by_item
    out["_deepen"] = meta
    return out
