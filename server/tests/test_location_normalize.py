"""Unit tests for location normalization (TSK-35)."""

from __future__ import annotations

import unittest

from app.services.location_normalize import normalize_location


class LocationNormalizeTests(unittest.TestCase):
    def test_remote_us_dash(self) -> None:
        result = normalize_location("Remote - US")
        self.assertTrue(result.remote)
        self.assertEqual(result.countries, ["US"])
        self.assertEqual(result.status, "ok")

    def test_remote_united_states(self) -> None:
        result = normalize_location("Remote, United States")
        self.assertTrue(result.remote)
        self.assertEqual(result.countries, ["US"])
        self.assertEqual(result.status, "ok")

    def test_london_uk(self) -> None:
        result = normalize_location("London, UK")
        self.assertFalse(result.remote)
        self.assertEqual(result.countries, ["GB"])
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.city, "London")

    def test_empty_failed(self) -> None:
        result = normalize_location("")
        self.assertEqual(result.status, "failed")
        self.assertFalse(result.remote)
        self.assertEqual(result.countries, [])

    def test_no_country_no_remote_failed(self) -> None:
        result = normalize_location("Somewhere cool")
        self.assertEqual(result.status, "failed")

    def test_remote_only_partial(self) -> None:
        result = normalize_location("Remote")
        self.assertTrue(result.remote)
        self.assertEqual(result.countries, [])
        self.assertEqual(result.status, "partial")

    def test_multi_location(self) -> None:
        result = normalize_location("New York, NY / London, UK")
        self.assertIn("GB", result.countries)
        self.assertEqual(result.status, "ok")

    def test_raw_unchanged_concept(self) -> None:
        raw = "Remote - US"
        result = normalize_location(raw)
        self.assertEqual(raw, "Remote - US")
        self.assertEqual(result.countries, ["US"])

    def test_city_infers_country(self) -> None:
        paris = normalize_location("Paris")
        self.assertEqual(paris.countries, ["FR"])
        self.assertEqual(paris.status, "ok")

        bay = normalize_location("San Francisco Bay Area")
        self.assertEqual(bay.countries, ["US"])
        self.assertEqual(bay.status, "ok")

        warsaw = normalize_location("Warsaw")
        self.assertEqual(warsaw.countries, ["PL"])

        london_remote = normalize_location("London (Remote)")
        self.assertTrue(london_remote.remote)
        self.assertEqual(london_remote.countries, ["GB"])
        self.assertEqual(london_remote.status, "ok")


if __name__ == "__main__":
    unittest.main()
