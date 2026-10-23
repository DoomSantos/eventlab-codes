"""AEST session window helpers."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from server.store import (
    aest_day_end,
    aest_day_start,
    normalize_window,
    session_meta,
    window_since_iso,
)


class WindowTests(unittest.TestCase):
    def test_aliases(self) -> None:
        self.assertEqual(normalize_window("anytime"), "all")
        self.assertEqual(normalize_window("week"), "7d")
        self.assertEqual(normalize_window("Today"), "today")

    def test_today_is_aest_midnight(self) -> None:
        # 2026-09-13 22:30 UTC = 2026-09-14 08:30 AEST → day starts 2026-09-13 14:00 UTC
        now = datetime(2026, 9, 13, 22, 30, tzinfo=timezone.utc)
        since = window_since_iso("today", now=now)
        self.assertEqual(since, "2026-09-13T14:00:00Z")
        start = aest_day_start(now)
        end = aest_day_end(now)
        self.assertEqual(start.year, 2026)
        self.assertEqual(start.month, 9)
        self.assertEqual(start.day, 14)
        self.assertEqual(start.hour, 0)
        self.assertEqual(end.day, 15)
        self.assertEqual(end.hour, 0)
        meta = session_meta(now)
        self.assertEqual(meta["day"], "2026-09-14")
        self.assertEqual(meta["ends_at"], "2026-09-14T14:00:00Z")

    def test_all_has_no_lower_bound(self) -> None:
        self.assertIsNone(window_since_iso("all"))


if __name__ == "__main__":
    unittest.main()
