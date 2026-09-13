"""Track fingerprint match helper."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from collector.verify import (
    FINGERPRINT,
    TA_START_FINGERPRINT,
    match_path,
    match_time_attack_start,
)


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


class TimeAttackStartTests(unittest.TestCase):
    def test_ta_captures_match_start_fingerprint(self) -> None:
        if not TA_START_FINGERPRINT.is_file():
            self.skipTest("TA start fingerprint missing")
        root = Path(__file__).resolve().parent / "captures" / "albert-park"
        files = sorted(root.glob("*_time_attack.json"))
        if len(files) < 3:
            self.skipTest("Need time_attack captures")
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            result = match_time_attack_start(data["path"])
            self.assertTrue(result["matched"], path.name)
            self.assertEqual(result["mode"], "time_attack")

    def test_normal_cleans_miss_ta_start(self) -> None:
        if not TA_START_FINGERPRINT.is_file():
            self.skipTest("TA start fingerprint missing")
        root = Path(__file__).resolve().parent / "captures" / "albert-park"
        files = sorted(root.glob("*_clean.json"))[:5]
        if not files:
            self.skipTest("Need clean captures")
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            result = match_time_attack_start(data["path"])
            self.assertFalse(result["matched"], path.name)
            self.assertIsNone(result["mode"])


if __name__ == "__main__":
    unittest.main()
