"""Tests for gap-based integrity classification."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from collector.integrity import classify_integrity, is_rewindish_gap, meaningful_jumps
from collector.lap_detect import GapEvent


def _gap(
    *,
    jump_m: float,
    duration_s: float = 5.0,
    lap_time_before_s: float = 30.0,
) -> GapEvent:
    return GapEvent(
        duration_s=duration_s,
        before_x=0.0,
        before_y=0.0,
        before_z=0.0,
        after_x=jump_m,
        after_y=0.0,
        after_z=0.0,
        jump_m=jump_m,
        lap_time_before_s=lap_time_before_s,
    )


class IntegrityTests(unittest.TestCase):
    def test_clean_when_no_gaps(self) -> None:
        self.assertEqual(classify_integrity([]), "clean")

    def test_pause_scale_jump_is_clean(self) -> None:
        self.assertEqual(classify_integrity([_gap(jump_m=3.0)]), "clean")

    def test_rewind_scale_mid_lap_is_rewound(self) -> None:
        self.assertEqual(
            classify_integrity([_gap(jump_m=180.0, lap_time_before_s=40.0)]),
            "rewound",
        )

    def test_pre_start_spawn_teleport_ignored(self) -> None:
        gaps = [_gap(jump_m=109.0, duration_s=12.0, lap_time_before_s=0.0)]
        self.assertEqual(classify_integrity(gaps, lap_time_s=91.0), "clean")
        self.assertEqual(meaningful_jumps(gaps, lap_time_s=91.0), [])

    def test_stale_prior_attempt_gap_ignored(self) -> None:
        # Bundled event-restart noise: jump while timer was past the finished lap.
        gaps = [_gap(jump_m=199.0, duration_s=21.0, lap_time_before_s=91.7)]
        self.assertEqual(classify_integrity(gaps, lap_time_s=91.02), "clean")

    def test_real_bundled_restart_capture_is_clean(self) -> None:
        root = Path(__file__).resolve().parent / "captures" / "albert-park"
        path = root / "20260913T133349411638_unknown.json"
        if not path.is_file():
            self.skipTest("bundled restart capture missing")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            classify_integrity(data.get("gaps") or [], lap_time_s=data.get("lap_time_s")),
            "clean",
        )

    def test_force_rewound(self) -> None:
        self.assertEqual(classify_integrity([], force_rewound=True), "rewound")

    def test_rewindish_detects_short_mid_lap_jump(self) -> None:
        self.assertTrue(
            is_rewindish_gap(_gap(jump_m=200.0, duration_s=5.0, lap_time_before_s=40.0))
        )
        self.assertFalse(
            is_rewindish_gap(_gap(jump_m=200.0, duration_s=21.0, lap_time_before_s=40.0))
        )
        self.assertFalse(
            is_rewindish_gap(_gap(jump_m=200.0, duration_s=5.0, lap_time_before_s=0.0))
        )


if __name__ == "__main__":
    unittest.main()
