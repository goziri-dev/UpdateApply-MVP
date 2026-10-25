"""Directory CSV mapping helpers (no network)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services.board_directory import load_directory_rows


class LoadDirectoryRowsTests(unittest.TestCase):
    def test_maps_columns(self) -> None:
        csv_text = (
            "ats_vendor,company_name,board_slug,last_crawled\n"
            "greenhouse,Acme,acme,2026-08-01\n"
            "lever,Beta Inc,betainc,2026-08-01\n"
            "workday,Nope,nope,2026-08-01\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dir.csv"
            path.write_text(csv_text, encoding="utf-8")
            rows = load_directory_rows(path)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["vendor"], "greenhouse")
        self.assertEqual(rows[0]["slug"], "acme")
        self.assertEqual(rows[0]["company_name"], "Acme")
        self.assertEqual(rows[2]["vendor"], "workday")


if __name__ == "__main__":
    unittest.main()
