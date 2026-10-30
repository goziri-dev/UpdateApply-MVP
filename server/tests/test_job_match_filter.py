"""Unit tests for Pass 1 title / seniority / location filters (TSK-36)."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.services.job_match import (
    DEFAULT_LOOKBACK_HOURS,
    MAX_STALE_LOOKBACK_HOURS,
    _title_prefilter_clause,
    effective_lookback_hours,
    location_allows,
    seniority_allows,
    title_matches,
)


class TitleMatchTests(unittest.TestCase):
    def test_phrase_hit(self) -> None:
        self.assertTrue(title_matches("Software Engineer", "Senior Software Engineer"))

    def test_token_hit(self) -> None:
        self.assertTrue(
            title_matches("Backend Engineer", "Staff Backend Platform Engineer")
        )

    def test_title_miss(self) -> None:
        self.assertFalse(title_matches("Product Designer", "Software Engineer"))

    def test_confirmed_exact_title_phrase(self) -> None:
        # Matcher only uses confirmed titles — not profile skills.
        self.assertTrue(title_matches("Python Engineer", "Senior Python Engineer"))
        self.assertFalse(title_matches("Data Scientist", "Senior Python Engineer"))

    def test_role_family_tail(self) -> None:
        self.assertTrue(
            title_matches(
                "Digital Marketing Specialist", "Content Marketing Specialist"
            )
        )

    def test_domain_stem_soft_match(self) -> None:
        self.assertTrue(
            title_matches("Marketing Coordinator", "Product Marketing Manager")
        )
        self.assertTrue(
            title_matches("Content Creator", "Content Marketing Specialist")
        )
        self.assertTrue(
            title_matches("Social Media Manager", "Product Marketing Manager")
        )
        self.assertFalse(title_matches("Social Media Manager", "Software Engineer"))
        self.assertFalse(
            title_matches("Social Media Manager", "Senior Software Engineer, Growth")
        )


class TitlePrefilterTests(unittest.TestCase):
    def test_builds_clause_for_confirmed_titles(self) -> None:
        clause = _title_prefilter_clause(
            ["Social Media Manager", "Digital Marketing Specialist"]
        )
        self.assertIsNotNone(clause)

    def test_empty_titles_yield_no_clause(self) -> None:
        self.assertIsNone(_title_prefilter_clause([]))


class SeniorityTests(unittest.TestCase):
    def test_no_token_kept(self) -> None:
        ok, explicit = seniority_allows(["senior"], "Software Engineer")
        self.assertTrue(ok)
        self.assertFalse(explicit)

    def test_contradiction_junior_vs_senior(self) -> None:
        ok, _ = seniority_allows(["senior"], "Junior Software Engineer")
        self.assertFalse(ok)

    def test_contradiction_manager_vs_ic(self) -> None:
        ok, _ = seniority_allows(["senior"], "Engineering Manager")
        self.assertFalse(ok)
        ok_exec, _ = seniority_allows(["senior"], "Director of Engineering")
        self.assertFalse(ok_exec)
        # Function "… Manager" titles stay eligible for IC bands.
        ok_ic, _ = seniority_allows(["senior", "mid"], "Product Marketing Manager")
        self.assertTrue(ok_ic)

    def test_explicit_senior(self) -> None:
        ok, explicit = seniority_allows(["senior"], "Senior Software Engineer")
        self.assertTrue(ok)
        self.assertTrue(explicit)


class LocationFilterTests(unittest.TestCase):
    def _prefs(self, **kwargs: object) -> SimpleNamespace:
        base = {
            "id": uuid4(),
            "remote_preference": "remote_ok",
            "countries": ["United States"],
            "city": None,
        }
        base.update(kwargs)
        return SimpleNamespace(**base)

    def test_failed_parse_excluded(self) -> None:
        ok, _ = location_allows(
            self._prefs(),  # type: ignore[arg-type]
            remote=False,
            countries=[],
            parse_status="failed",
        )
        self.assertFalse(ok)

    def test_wrong_country(self) -> None:
        ok, _ = location_allows(
            self._prefs(),  # type: ignore[arg-type]
            remote=False,
            countries=["GB"],
            parse_status="ok",
        )
        self.assertFalse(ok)

    def test_remote_only_requires_remote(self) -> None:
        ok, _ = location_allows(
            self._prefs(remote_preference="remote_only"),  # type: ignore[arg-type]
            remote=False,
            countries=["US"],
            parse_status="ok",
        )
        self.assertFalse(ok)

    def test_remote_us_ok(self) -> None:
        ok, phrase = location_allows(
            self._prefs(remote_preference="remote_only"),  # type: ignore[arg-type]
            remote=True,
            countries=["US"],
            parse_status="ok",
        )
        self.assertTrue(ok)
        self.assertIn("remote", phrase)

    def test_remote_ok_allows_remote_without_country_overlap(self) -> None:
        # Ireland prefs + US-tagged remote hub still surfaces for remote_ok.
        ok, phrase = location_allows(
            self._prefs(countries=["Ireland"]),  # type: ignore[arg-type]
            remote=True,
            countries=["US"],
            parse_status="ok",
        )
        self.assertTrue(ok)
        self.assertIn("remote", phrase)

    def test_remote_ok_still_filters_onsite_country(self) -> None:
        ok, _ = location_allows(
            self._prefs(countries=["Ireland"]),  # type: ignore[arg-type]
            remote=False,
            countries=["US"],
            parse_status="ok",
        )
        self.assertFalse(ok)


class EffectiveLookbackTests(unittest.TestCase):
    def _session(self, max_seen: datetime | None) -> MagicMock:
        session = MagicMock()
        session.exec.return_value.one.return_value = max_seen
        return session

    def test_fresh_catalog_keeps_configured(self) -> None:
        now = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
        max_seen = now - timedelta(hours=12)
        hours = effective_lookback_hours(
            self._session(max_seen),
            configured=DEFAULT_LOOKBACK_HOURS,
            now=now,
        )
        self.assertEqual(hours, DEFAULT_LOOKBACK_HOURS)

    def test_stale_catalog_widens(self) -> None:
        now = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
        max_seen = now - timedelta(hours=120)  # 5 days
        hours = effective_lookback_hours(
            self._session(max_seen),
            configured=DEFAULT_LOOKBACK_HOURS,
            now=now,
        )
        self.assertEqual(hours, 120 + 24)
        self.assertGreater(hours, DEFAULT_LOOKBACK_HOURS)

    def test_stale_catalog_caps_at_max(self) -> None:
        now = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
        max_seen = now - timedelta(days=30)
        hours = effective_lookback_hours(
            self._session(max_seen),
            configured=DEFAULT_LOOKBACK_HOURS,
            now=now,
        )
        self.assertEqual(hours, MAX_STALE_LOOKBACK_HOURS)

    def test_empty_catalog_keeps_configured(self) -> None:
        hours = effective_lookback_hours(
            self._session(None),
            configured=DEFAULT_LOOKBACK_HOURS,
        )
        self.assertEqual(hours, DEFAULT_LOOKBACK_HOURS)


if __name__ == "__main__":
    unittest.main()
