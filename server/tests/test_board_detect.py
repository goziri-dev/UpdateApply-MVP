"""Unit tests for careers URL → vendor/slug detection (TSK-45)."""

from __future__ import annotations

import unittest

from app.services.board_detect import BoardDetectError, parse_careers_url


class ParseCareersUrlTests(unittest.TestCase):
    def test_greenhouse_boards(self) -> None:
        d = parse_careers_url("https://boards.greenhouse.io/discord")
        self.assertEqual(d.vendor, "greenhouse")
        self.assertEqual(d.slug, "discord")

    def test_greenhouse_job_boards_host(self) -> None:
        d = parse_careers_url("https://job-boards.greenhouse.io/stripe/jobs/123")
        self.assertEqual(d.vendor, "greenhouse")
        self.assertEqual(d.slug, "stripe")

    def test_lever(self) -> None:
        d = parse_careers_url("https://jobs.lever.co/canvasmedical")
        self.assertEqual(d.vendor, "lever")
        self.assertEqual(d.slug, "canvasmedical")

    def test_ashby(self) -> None:
        d = parse_careers_url("https://jobs.ashbyhq.com/linear")
        self.assertEqual(d.vendor, "ashby")
        self.assertEqual(d.slug, "linear")

    def test_duplicate_path_ok(self) -> None:
        a = parse_careers_url("https://boards.greenhouse.io/discord/jobs/1")
        b = parse_careers_url("https://boards.greenhouse.io/discord")
        self.assertEqual(a.vendor, b.vendor)
        self.assertEqual(a.slug, b.slug)

    def test_foreign_host(self) -> None:
        with self.assertRaises(BoardDetectError) as ctx:
            parse_careers_url("https://careers.example.com/jobs")
        self.assertEqual(ctx.exception.code, "unsupported_board")

    def test_empty(self) -> None:
        with self.assertRaises(BoardDetectError):
            parse_careers_url("   ")


if __name__ == "__main__":
    unittest.main()
