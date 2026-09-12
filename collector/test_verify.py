"""Track fingerprint match helper."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from collector.verify import FINGERPRINT, match_path


class MatchPathTests(unittest.TestCase):
    def test_fingerprint_self_match(self) -> None:
        if not FINGERPRINT.is_file():
            self.skipTest("Albert Park fingerprint missing")
        data = json.loads(FINGERPRINT.read_text(encoding="utf-8"))
        result = match_path(data["points"], data)
        self.assertTrue(result["matched"])
        self.assertEqual(result["track"], "Albert Park")

    def test_half_path_matches_with_live_threshold(self) -> None:
        if not FINGERPRINT.is_file():
            self.skipTest("Albert Park fingerprint missing")
        data = json.loads(FINGERPRINT.read_text(encoding="utf-8"))
        half = data["points"][: max(1, len(data["points"]) // 2)]
        strict = match_path(half, data, live=False)
        live = match_path(half, data, live=True)
        # Half coverage often fails strict 0.55; live threshold is more forgiving
        self.assertFalse(strict["matched"])
        self.assertTrue(live["matched"])


if __name__ == "__main__":
    unittest.main()
