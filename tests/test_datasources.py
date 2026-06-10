"""Tests for the ITSM data-layer pure helpers (no data files required)."""

import unittest

from app.datasources import _sanitize, parse_dt


class TestSanitize(unittest.TestCase):
    def test_dots_become_underscores(self):
        self.assertEqual(_sanitize("caller_id.vip"), "caller_id_vip")
        self.assertEqual(_sanitize("parent.ref_rm_release.u_risk"), "parent_ref_rm_release_u_risk")

    def test_lowercased_and_trimmed(self):
        self.assertEqual(_sanitize("  Short Description "), "short_description")

    def test_empty_falls_back(self):
        self.assertEqual(_sanitize("   "), "col")


class TestParseDt(unittest.TestCase):
    def test_iso_format(self):
        dt = parse_dt("2025-12-15 16:57:02")
        self.assertEqual((dt.year, dt.month, dt.day, dt.hour), (2025, 12, 15, 16))

    def test_us_slash_format(self):
        dt = parse_dt("4/3/2026 12:31")
        self.assertEqual((dt.year, dt.month, dt.day), (2026, 4, 3))

    def test_unknown_and_blank_return_none(self):
        self.assertIsNone(parse_dt("UNKNOWN"))
        self.assertIsNone(parse_dt(""))
        self.assertIsNone(parse_dt("not a date"))


if __name__ == "__main__":
    unittest.main()
