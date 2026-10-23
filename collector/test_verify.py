"""Track fingerprint match helper."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from collector.verify import (
    FINGERPRINT,
    TA_START_DIR,
    TA_START_FINGERPRINT,
    clear_fingerprint_cache,
    match_path,
    match_time_attack_start,
    resolve_ta_session_mode,
)


class MatchPathTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_fingerprint_cache()
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
    def setUp(self) -> None:
        clear_fingerprint_cache()

    def test_ta_captures_match_start_fingerprint(self) -> None:
        if not TA_START_FINGERPRINT.is_file():
            self.skipTest("TA start fingerprint missing")
        root = Path(__file__).resolve().parent / "captures" / "albert-park"
        files = sorted(root.glob("*_time_attack.json"))
        if len(files) < 3:
            self.skipTest("Need time_attack captures")
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            path_samples = data.get("path") or []
            wall = float(path_samples[-1]["t_s"]) if path_samples else 0.0
            lap = float(data.get("lap_time_s") or 0.0)
            # Skip abandoned/restart-bundled sessions (wall clock >> lap time)
            if lap > 0 and wall > lap * 2.5:
                continue
            result = match_time_attack_start(data["path"])
            self.assertTrue(result["matched"], path.name)
            self.assertEqual(result["mode"], "time_attack")
            self.assertEqual(result["track"], "Albert Park")

    def test_ta_start_matches_after_festival_teleport(self) -> None:
        """Loading TA from the festival prefixes open-world path before the pit grid."""
        if not TA_START_FINGERPRINT.is_file():
            self.skipTest("TA start fingerprint missing")
        root = Path(__file__).resolve().parent / "captures" / "albert-park"
        files = sorted(root.glob("*_time_attack.json"))
        data = None
        for path in files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            samples = payload.get("path") or []
            wall = float(samples[-1]["t_s"]) if samples else 0.0
            lap = float(payload.get("lap_time_s") or 0.0)
            if lap > 0 and wall > lap * 2.5:
                continue
            data = payload
            break
        if not data:
            self.skipTest("Need a Time Attack capture")
        prefix = [
            {"x": -2020.8, "z": -3108.4, "t_s": 0.0},
            {"x": -2021.0, "z": -3109.0, "t_s": 1.0},
        ]
        mixed = prefix + list(data["path"])
        self.assertFalse(match_time_attack_start(prefix)["matched"])
        result = match_time_attack_start(mixed)
        self.assertTrue(result["matched"], result)
        self.assertEqual(result["track"], "Albert Park")
        self.assertEqual(result["mode"], "time_attack")
        self.assertGreater(result.get("window_index") or 0, 0)

    def test_monza_ta_captures_match_slot_variants(self) -> None:
        monza_fp = TA_START_DIR / "autodromo-nazionale-monza-time-attack-start.json"
        if not monza_fp.is_file():
            self.skipTest("Monza TA start fingerprint missing")
        root = Path(__file__).resolve().parent / "captures" / "autodromo-nazionale-monza"
        files = sorted(root.glob("*_time_attack.json"))
        if len(files) < 2:
            self.skipTest("Need Monza time_attack captures")
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            path_samples = data.get("path") or []
            wall = float(path_samples[-1]["t_s"]) if path_samples else 0.0
            lap = float(data.get("lap_time_s") or 0.0)
            if lap > 0 and wall > lap * 2.5:
                continue
            result = match_time_attack_start(data["path"])
            self.assertTrue(result["matched"], path.name)
            self.assertEqual(result["mode"], "time_attack")
            self.assertEqual(result["track"], "Autodromo Nazionale Monza")
            self.assertIsNotNone(result.get("variant"))

    def test_monza_junior_ta_disambiguates_from_full(self) -> None:
        junior_fp = (
            TA_START_DIR
            / "autodromo-nazionale-monza-junior-course-time-attack-start.json"
        )
        if not junior_fp.is_file():
            self.skipTest("Monza Junior TA start fingerprint missing")
        root = (
            Path(__file__).resolve().parent
            / "captures"
            / "autodromo-nazionale-monza-junior-course"
        )
        files = sorted(root.glob("*_time_attack.json"))
        if len(files) < 2:
            self.skipTest("Need Monza Junior time_attack captures")
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            result = match_time_attack_start(data["path"])
            self.assertTrue(result["matched"], path.name)
            self.assertEqual(
                result["track"],
                "Autodromo Nazionale Monza Junior Course",
                path.name,
            )

    def test_monaco_ta_captures_match(self) -> None:
        monaco_fp = TA_START_DIR / "circuit-de-monaco-time-attack-start.json"
        if not monaco_fp.is_file():
            self.skipTest("Monaco TA start fingerprint missing")
        root = Path(__file__).resolve().parent / "captures" / "circuit-de-monaco"
        files = sorted(root.glob("*_time_attack.json"))
        if len(files) < 2:
            self.skipTest("Need Monaco time_attack captures")
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            result = match_time_attack_start(data["path"])
            self.assertTrue(result["matched"], path.name)
            self.assertEqual(result["track"], "Circuit de Monaco", path.name)
            self.assertEqual(result["mode"], "time_attack")

    def test_top_gear_ta_captures_match(self) -> None:
        tg_fp = TA_START_DIR / "top-gear-test-track-time-attack-start.json"
        if not tg_fp.is_file():
            self.skipTest("Top Gear TA start fingerprint missing")
        root = Path(__file__).resolve().parent / "captures" / "top-gear-test-track"
        files = sorted(root.glob("*_time_attack.json"))
        if len(files) < 2:
            self.skipTest("Need Top Gear time_attack captures")
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            result = match_time_attack_start(data["path"])
            self.assertTrue(result["matched"], path.name)
            self.assertEqual(result["track"], "Top Gear Test Track", path.name)
            self.assertEqual(result["mode"], "time_attack")
            path_hit = match_path(data["path"], live=True)
            self.assertTrue(path_hit["matched"], path.name)
            self.assertEqual(path_hit["track"], "Top Gear Test Track", path.name)
            self.assertTrue(path_hit.get("soft_corridor"), path.name)

    def test_brands_hatch_indy_ta_captures_match(self) -> None:
        indy_fp = TA_START_DIR / "brands-hatch-indy-circuit-time-attack-start.json"
        if not indy_fp.is_file():
            self.skipTest("Brands Hatch Indy TA start fingerprint missing")
        root = (
            Path(__file__).resolve().parent
            / "captures"
            / "brands-hatch-indy-circuit"
        )
        files = sorted(root.glob("*_time_attack.json"))
        if len(files) < 2:
            self.skipTest("Need Brands Hatch Indy time_attack captures")
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            result = match_time_attack_start(data["path"])
            self.assertTrue(result["matched"], path.name)
            self.assertEqual(result["track"], "Brands Hatch Indy Circuit", path.name)
            self.assertEqual(result["mode"], "time_attack")

    def test_brands_hatch_circuit_ta_captures_match(self) -> None:
        gp_fp = TA_START_DIR / "brands-hatch-circuit-time-attack-start.json"
        if not gp_fp.is_file():
            self.skipTest("Brands Hatch Circuit TA start fingerprint missing")
        root = (
            Path(__file__).resolve().parent / "captures" / "brands-hatch-circuit"
        )
        files = sorted(root.glob("*_time_attack.json"))
        long_files = []
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            samples = data.get("path") or []
            traveled = 0.0
            for a, b in zip(samples, samples[1:]):
                traveled += (
                    (float(b["x"]) - float(a["x"])) ** 2
                    + (float(b["z"]) - float(a["z"])) ** 2
                ) ** 0.5
            if traveled >= 2800:
                long_files.append((path, data))
        if len(long_files) < 2:
            self.skipTest("Need Brands Hatch Circuit time_attack captures")
        for path, data in long_files:
            result = match_time_attack_start(data["path"])
            self.assertTrue(result["matched"], path.name)
            self.assertEqual(result["track"], "Brands Hatch Circuit", path.name)
            self.assertEqual(result["mode"], "time_attack")

    def test_brands_hatch_gp_and_indy_do_not_cross_match(self) -> None:
        gp_fp = TA_START_DIR / "brands-hatch-circuit-time-attack-start.json"
        indy_fp = TA_START_DIR / "brands-hatch-indy-circuit-time-attack-start.json"
        if not gp_fp.is_file() or not indy_fp.is_file():
            self.skipTest("Brands Hatch TA start fingerprints missing")
        gp_root = Path(__file__).resolve().parent / "captures" / "brands-hatch-circuit"
        indy_root = (
            Path(__file__).resolve().parent / "captures" / "brands-hatch-indy-circuit"
        )
        gp_files = sorted(gp_root.glob("*_time_attack.json"))
        indy_files = sorted(indy_root.glob("*_time_attack.json"))
        if len(gp_files) < 1 or len(indy_files) < 1:
            self.skipTest("Need Brands Hatch GP and Indy captures")
        gp = json.loads(gp_files[-1].read_text(encoding="utf-8"))
        indy = json.loads(indy_files[0].read_text(encoding="utf-8"))
        gp_hit = match_time_attack_start(gp["path"])
        indy_hit = match_time_attack_start(indy["path"])
        self.assertEqual(gp_hit.get("track"), "Brands Hatch Circuit", gp_files[-1].name)
        self.assertEqual(
            indy_hit.get("track"),
            "Brands Hatch Indy Circuit",
            indy_files[0].name,
        )

    def test_monza_does_not_match_albert_park_track(self) -> None:
        root = Path(__file__).resolve().parent / "captures" / "autodromo-nazionale-monza"
        files = sorted(root.glob("*_time_attack.json"))
        if not files:
            self.skipTest("Need Monza captures")
        data = json.loads(files[0].read_text(encoding="utf-8"))
        result = match_path(data["path"], live=True)
        self.assertFalse(result["matched"], files[0].name)

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


class TimeAttackSessionModeTests(unittest.TestCase):
    def test_offset_start_arms_session(self) -> None:
        mode, active = resolve_ta_session_mode(
            matched=True, lap_number=1, session_active=False
        )
        self.assertEqual(mode, "time_attack")
        self.assertTrue(active)

    def test_later_laps_inherit_without_start_match(self) -> None:
        mode, active = resolve_ta_session_mode(
            matched=False, lap_number=2, session_active=True
        )
        self.assertEqual(mode, "time_attack")
        self.assertTrue(active)
        mode50, active50 = resolve_ta_session_mode(
            matched=False, lap_number=50, session_active=True
        )
        self.assertEqual(mode50, "time_attack")
        self.assertTrue(active50)

    def test_new_non_ta_first_lap_clears_session(self) -> None:
        mode, active = resolve_ta_session_mode(
            matched=False, lap_number=1, session_active=True
        )
        self.assertEqual(mode, "")
        self.assertFalse(active)

    def test_normal_event_never_arms(self) -> None:
        mode, active = resolve_ta_session_mode(
            matched=False, lap_number=3, session_active=False
        )
        self.assertEqual(mode, "")
        self.assertFalse(active)

    def test_exploit_path_new_event_lap1_does_not_count(self) -> None:
        """TA start arms, then a different event's lap 1 must not inherit Mode."""
        _, active = resolve_ta_session_mode(
            matched=True, lap_number=1, session_active=False
        )
        self.assertTrue(active)
        mode, active = resolve_ta_session_mode(
            matched=False, lap_number=1, session_active=active
        )
        self.assertEqual(mode, "")
        self.assertFalse(active)


if __name__ == "__main__":
    unittest.main()
