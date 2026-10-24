"""Quick sanity checks for collector internals (no game required)."""

from __future__ import annotations

import struct
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from collector.app import CollectorState
from collector.cloud import DeviceConfig
from collector.lap_detect import LapDetector, PathSample
from collector.packet import PACKET_SIZE, class_from_pi, format_lap_time, parse_packet
from collector.store import LapStore
from collector.build_ta_start_fingerprint import layout_meters_for
from collector.tracks import load_track_names


def _blank_packet(**overrides: int | float) -> bytes:
    buf = bytearray(PACKET_SIZE)
    # Defaults: race on, class A (3), PI 699, lap fields
    struct.pack_into("<i", buf, 0, 1)
    struct.pack_into("<I", buf, 4, 1000)
    struct.pack_into("<i", buf, 212, 1234)  # ordinal
    struct.pack_into("<i", buf, 216, 3)  # class A
    struct.pack_into("<i", buf, 220, 699)  # PI
    struct.pack_into("<f", buf, 244, 0.0)  # pos x
    struct.pack_into("<f", buf, 248, 0.0)  # pos y
    struct.pack_into("<f", buf, 252, 0.0)  # pos z
    struct.pack_into("<f", buf, 296, 0.0)  # best
    struct.pack_into("<f", buf, 300, 0.0)  # last
    struct.pack_into("<f", buf, 304, 10.0)  # current
    struct.pack_into("<H", buf, 312, 0)  # lap number
    for key, value in overrides.items():
        if key == "is_race_on":
            struct.pack_into("<i", buf, 0, int(value))
        elif key == "lap_number":
            struct.pack_into("<H", buf, 312, int(value))
        elif key == "last_lap":
            struct.pack_into("<f", buf, 300, float(value))
        elif key == "current_lap":
            struct.pack_into("<f", buf, 304, float(value))
        elif key == "pos_x":
            struct.pack_into("<f", buf, 244, float(value))
        elif key == "pos_z":
            struct.pack_into("<f", buf, 252, float(value))
        elif key == "car_class":
            struct.pack_into("<i", buf, 216, int(value))
        elif key == "car_pi":
            struct.pack_into("<i", buf, 220, int(value))
    return bytes(buf)


class PacketTests(unittest.TestCase):
    def test_parse_class_pi(self) -> None:
        tel = parse_packet(_blank_packet())
        assert tel is not None
        self.assertEqual(tel.class_name, "A")
        self.assertEqual(tel.car_pi, 699)
        self.assertEqual(tel.class_pi_label, "A 699")

    def test_format_lap_time(self) -> None:
        self.assertEqual(format_lap_time(84.102), "1:24.102")
        self.assertEqual(format_lap_time(9.5), "9.500")

    def test_class_from_pi_fh6(self) -> None:
        self.assertEqual(class_from_pi(800), "S1")
        self.assertEqual(class_from_pi(900), "S2")
        self.assertEqual(class_from_pi(998), "R")
        self.assertEqual(class_from_pi(999), "X")


class LapDetectTests(unittest.TestCase):
    def test_detects_completed_lap(self) -> None:
        detector = LapDetector()
        t0 = parse_packet(_blank_packet(lap_number=0, last_lap=0))
        t1 = parse_packet(_blank_packet(lap_number=1, last_lap=84.102))
        assert t0 and t1
        self.assertIsNone(detector.feed(t0))
        completed = detector.feed(t1)
        assert completed is not None
        self.assertAlmostEqual(completed.lap_time_s, 84.102, places=3)
        self.assertEqual(completed.class_name, "A")
        self.assertEqual(completed.car_pi, 699)
        self.assertFalse(completed.suspect_rewind)

    def test_event_restart_resets_segment_without_force_rewound(self) -> None:
        """Long menu/load gap + timer→0 must not poison the next attempt."""
        detector = LapDetector()
        times = iter([100.0, 100.1, 121.0, 121.1, 121.2])

        def fake_mono() -> float:
            return next(times)

        with unittest.mock.patch("collector.lap_detect.time.monotonic", fake_mono):
            start = parse_packet(
                _blank_packet(lap_number=0, last_lap=0, current_lap=0.0, pos_x=0.0)
            )
            mid = parse_packet(
                _blank_packet(lap_number=0, last_lap=0, current_lap=60.0, pos_x=100.0)
            )
            assert start and mid
            self.assertIsNone(detector.feed(start))
            self.assertIsNone(detector.feed(mid))
            # 21s stream gap + ~200m jump while abandoning the attempt
            after_restart = parse_packet(
                _blank_packet(lap_number=0, last_lap=0, current_lap=0.0, pos_x=300.0)
            )
            assert after_restart
            self.assertIsNone(detector.feed(after_restart))
            self.assertEqual(detector._gaps_this_lap, [])
            self.assertFalse(detector._force_rewound)
            done = parse_packet(
                _blank_packet(lap_number=1, last_lap=90.0, current_lap=0.0, pos_x=310.0)
            )
            assert done
            completed = detector.feed(done)
        assert completed is not None
        self.assertEqual(completed.gaps, ())
        self.assertFalse(completed.force_rewound)

    def test_festival_load_teleport_starts_fresh_path(self) -> None:
        """Open world → EventLab pit spawn must drop the festival path."""
        detector = LapDetector()
        times = iter([50.0, 50.2, 66.0, 66.2])

        def fake_mono() -> float:
            return next(times)

        with unittest.mock.patch("collector.lap_detect.time.monotonic", fake_mono):
            festival = parse_packet(
                _blank_packet(
                    lap_number=0,
                    last_lap=0,
                    current_lap=0.0,
                    pos_x=-2020.0,
                    pos_z=-3108.0,
                )
            )
            pit = parse_packet(
                _blank_packet(
                    lap_number=0,
                    last_lap=0,
                    current_lap=0.0,
                    pos_x=-5822.0,
                    pos_z=-1998.0,
                )
            )
            assert festival and pit
            self.assertIsNone(detector.feed(festival))
            self.assertIsNone(detector.feed(pit))
            path = detector.current_path
            self.assertGreaterEqual(len(path), 1)
            self.assertAlmostEqual(path[0].x, -5822.0, places=0)
            self.assertAlmostEqual(path[0].z, -1998.0, places=0)
            self.assertTrue(all(p.x < -5000 for p in path))

    def test_nearby_festival_teleport_starts_fresh_path(self) -> None:
        """Albert Park paddock→pits is ~1300 m, under the old 1500 m ignore."""
        detector = LapDetector()
        times = iter([50.0, 50.2, 62.8, 63.0])

        def fake_mono() -> float:
            return next(times)

        with unittest.mock.patch("collector.lap_detect.time.monotonic", fake_mono):
            paddock = parse_packet(
                _blank_packet(
                    lap_number=0,
                    last_lap=0,
                    current_lap=0.0,
                    pos_x=-7137.0,
                    pos_z=-2069.0,
                )
            )
            pit = parse_packet(
                _blank_packet(
                    lap_number=0,
                    last_lap=0,
                    current_lap=0.0,
                    pos_x=-5822.0,
                    pos_z=-1998.0,
                )
            )
            assert paddock and pit
            self.assertIsNone(detector.feed(paddock))
            self.assertIsNone(detector.feed(pit))
            path = detector.current_path
            self.assertGreaterEqual(len(path), 1)
            self.assertAlmostEqual(path[0].x, -5822.0, places=0)
            self.assertTrue(all(abs(p.x + 5822.0) < 30 for p in path))

    def test_short_rewind_to_start_carries_force_rewound(self) -> None:
        detector = LapDetector()
        times = iter([200.0, 200.1, 205.2, 205.3, 205.4])

        def fake_mono() -> float:
            return next(times)

        with unittest.mock.patch("collector.lap_detect.time.monotonic", fake_mono):
            start = parse_packet(
                _blank_packet(lap_number=0, last_lap=0, current_lap=0.0, pos_x=0.0)
            )
            mid = parse_packet(
                _blank_packet(lap_number=0, last_lap=0, current_lap=40.0, pos_x=100.0)
            )
            assert start and mid
            detector.feed(start)
            detector.feed(mid)
            rewound = parse_packet(
                _blank_packet(lap_number=0, last_lap=0, current_lap=0.2, pos_x=300.0)
            )
            assert rewound
            detector.feed(rewound)
            self.assertTrue(detector._force_rewound)
            done = parse_packet(
                _blank_packet(lap_number=1, last_lap=88.0, current_lap=0.0, pos_x=310.0)
            )
            assert done
            completed = detector.feed(done)
        assert completed is not None
        self.assertTrue(completed.force_rewound)

    def test_finish_line_keeps_full_path(self) -> None:
        """Lap timer→0 on the finish packet must not wipe the path (TA detect needs it)."""
        detector = LapDetector()
        times = iter([10.0, 10.3, 10.6, 10.9, 11.2])

        def fake_mono() -> float:
            return next(times)

        with unittest.mock.patch("collector.lap_detect.time.monotonic", fake_mono):
            self.assertIsNone(
                detector.feed(
                    parse_packet(
                        _blank_packet(
                            lap_number=0, last_lap=0, current_lap=0.0, pos_x=0.0
                        )
                    )
                )
            )
            self.assertIsNone(
                detector.feed(
                    parse_packet(
                        _blank_packet(
                            lap_number=0, last_lap=0, current_lap=30.0, pos_x=50.0
                        )
                    )
                )
            )
            self.assertIsNone(
                detector.feed(
                    parse_packet(
                        _blank_packet(
                            lap_number=0, last_lap=0, current_lap=60.0, pos_x=100.0
                        )
                    )
                )
            )
            self.assertIsNone(
                detector.feed(
                    parse_packet(
                        _blank_packet(
                            lap_number=0, last_lap=0, current_lap=90.0, pos_x=150.0
                        )
                    )
                )
            )
            completed = detector.feed(
                parse_packet(
                    _blank_packet(
                        lap_number=1,
                        last_lap=91.0,
                        current_lap=0.0,
                        pos_x=200.0,
                    )
                )
            )
        assert completed is not None
        self.assertGreaterEqual(len(completed.path), 4)
        self.assertAlmostEqual(completed.path[0].x, 0.0, places=1)
        self.assertAlmostEqual(completed.lap_time_s, 91.0, places=3)



class StoreTests(unittest.TestCase):
    def test_keeps_best_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LapStore(Path(tmp) / "laps.db")
            _, improved = store.upsert_best(
                track="Albert Park",
                player_name="Tester",
                lap_time_s=90.0,
                class_name="A",
                car_pi=699,
                car_ordinal=1,
            )
            self.assertTrue(improved)
            _, improved2 = store.upsert_best(
                track="Albert Park",
                player_name="Tester",
                lap_time_s=95.0,
                class_name="A",
                car_pi=699,
                car_ordinal=1,
            )
            self.assertFalse(improved2)
            _, improved3 = store.upsert_best(
                track="Albert Park",
                player_name="Tester",
                lap_time_s=88.0,
                class_name="A",
                car_pi=699,
                car_ordinal=1,
            )
            self.assertTrue(improved3)
            laps = store.all_laps()
            self.assertEqual(len(laps), 1)
            self.assertAlmostEqual(laps[0].lap_time_s, 88.0)
            store.close()


class TrackNameTests(unittest.TestCase):
    def test_includes_staged_time_attack_tracks(self) -> None:
        names = load_track_names()
        self.assertIn("Albert Park", names)
        self.assertIn("Brands Hatch Circuit", names)
        self.assertIn("Brands Hatch Indy Circuit", names)
        self.assertIn("Circuit de Monaco", names)
        self.assertIn("Top Gear Test Track", names)


class LanAddressTests(unittest.TestCase):
    def test_lan_ips_skip_loopback(self) -> None:
        from collector.app import lan_ipv4_addresses

        for ip in lan_ipv4_addresses():
            self.assertFalse(ip.startswith("127."))
            self.assertFalse(ip.startswith("169.254."))


class DriverUiTests(unittest.TestCase):
    def test_driver_page_has_setup_and_troubleshooting(self) -> None:
        html = (
            Path(__file__).resolve().parent / "static" / "index.html"
        ).read_text(encoding="utf-8")
        for needle in (
            "Claim invite",
            "Data Out",
            "Xbox Series X|S",
            "127.0.0.1",
            "Waiting for game",
            "Windows blocked the program",
            "Lap says Rewound",
            "Can't reach the timing board",
            "class=\"lab-only\"",
            "?lab=1",
            "dsr-select.js",
            "Not a Time Attack event",
            "Clean Time Attack laps upload automatically",
        ):
            self.assertIn(needle, html)
        self.assertNotIn("Save lap", html)
        self.assertIn("id=\"setup-box\"", html)


class TimeAttackPresenceAndUploadTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = LapStore(Path(self._tmp.name) / "laps.db")
        self.state = CollectorState(self.store, ["Albert Park"])
        self.fake = unittest.mock.Mock()
        self.fake.cfg = DeviceConfig(
            api_base="http://127.0.0.1:9",
            device_token="tok",
            display_name="DoomSantos",
        )
        self.fake.presence.return_value = {}
        self.fake.upload_lap.return_value = {"lap_time": "1:49.635"}
        self.state.cloud = self.fake

    def tearDown(self) -> None:
        self.store.close()
        self._tmp.cleanup()

    def test_presence_skips_open_world(self) -> None:
        self.state.live = parse_packet(_blank_packet(is_race_on=1))
        self.state.packets_per_sec = 60
        self.state.ta_session_active = False
        self.state.send_presence()
        self.fake.presence.assert_not_called()

    def test_presence_sends_during_time_attack(self) -> None:
        self.state.live = parse_packet(_blank_packet(is_race_on=1))
        self.state.packets_per_sec = 60
        self.state.ta_session_active = True
        self.state.send_presence()
        self.fake.presence.assert_called_once()
        payload = self.fake.presence.call_args[0][0]
        self.assertTrue(payload["racing"])
        self.assertEqual(payload["mode"], "time_attack")
        self.assertEqual(payload["track"], "Albert Park")

    def test_presence_clears_after_leaving_time_attack(self) -> None:
        self.state.live = parse_packet(_blank_packet(is_race_on=1))
        self.state.packets_per_sec = 60
        self.state.ta_session_active = True
        self.state.send_presence()
        self.state.ta_session_active = False
        self.state.send_presence()
        self.assertEqual(self.fake.presence.call_count, 2)
        payload = self.fake.presence.call_args[0][0]
        self.assertFalse(payload["racing"])
        self.assertEqual(payload["mode"], "")

    def test_live_path_arms_time_attack_session(self) -> None:
        path = tuple(
            PathSample(
                t_s=i * 0.2,
                x=float(i * 4),
                y=0.0,
                z=0.0,
                speed_mps=20.0,
                lap_time_s=i * 0.2,
            )
            for i in range(16)
        )
        with unittest.mock.patch.object(
            type(self.state.detector),
            "current_path",
            new=unittest.mock.PropertyMock(return_value=path),
        ):
            with unittest.mock.patch("collector.app.match_time_attack_start") as matched:
                matched.return_value = {
                    "matched": True,
                    "track": "Albert Park",
                    "variant": "primary",
                    "distance_m": 2.0,
                    "coverage": 0.9,
                }
                self.state._last_live_ta_check = 0.0
                self.state._maybe_arm_ta_live()
        self.assertTrue(self.state.ta_session_active)
        self.assertEqual(self.state.track, "Albert Park")
        self.assertEqual(self.state.ta_session_track, "Albert Park")

    def test_auto_upload_skips_non_time_attack_laps(self) -> None:
        with unittest.mock.patch("collector.app.match_path") as path_hit:
            with unittest.mock.patch("collector.app.match_time_attack_start") as ta_hit:
                path_hit.return_value = {
                    "matched": False,
                    "track": None,
                    "distance_m": 99.0,
                    "coverage": 0.1,
                    "path_points": 4,
                }
                ta_hit.return_value = {
                    "matched": False,
                    "track": "Albert Park",
                    "distance_m": 99.0,
                    "coverage": 0.1,
                }
                self.state.handle_packet(_blank_packet(lap_number=0, last_lap=0.0))
                self.state.handle_packet(_blank_packet(lap_number=1, last_lap=84.1))
        self.assertEqual(len(self.state.session_laps), 1)
        self.assertEqual(self.state.session_laps[0].mode, "")
        self.assertEqual(self.state._cloud_queue, [])
        self.assertIn("not a Time Attack event", self.state.cloud_last_ok)

    def test_auto_upload_queues_time_attack_laps(self) -> None:
        with unittest.mock.patch("collector.app.match_path") as path_hit:
            with unittest.mock.patch("collector.app.match_time_attack_start") as ta_hit:
                path_hit.return_value = {
                    "matched": True,
                    "track": "Albert Park",
                    "distance_m": 2.0,
                    "coverage": 0.9,
                    "path_points": 40,
                }
                ta_hit.return_value = {
                    "matched": True,
                    "track": "Albert Park",
                    "variant": "primary",
                    "distance_m": 2.0,
                    "coverage": 0.9,
                }
                self.state.handle_packet(_blank_packet(lap_number=0, last_lap=0.0))
                self.state.handle_packet(_blank_packet(lap_number=1, last_lap=84.1))
        self.assertEqual(self.state.session_laps[0].mode, "time_attack")
        self.assertEqual(self.state._cloud_queue, [1])

    def test_monza_later_laps_stay_on_full_layout(self) -> None:
        tracks = [
            "Autodromo Nazionale Monza",
            "Autodromo Nazionale Monza Junior Course",
        ]
        store = LapStore(Path(self._tmp.name) / "monza.db")
        state = CollectorState(store, tracks)
        state.cloud = self.fake
        ta_hits = [
            {
                "matched": True,
                "track": "Autodromo Nazionale Monza",
                "variant": "slot-1",
                "distance_m": 1.5,
                "coverage": 0.95,
            },
            {
                "matched": True,
                "track": "Autodromo Nazionale Monza Junior Course",
                "variant": "slot-1",
                "distance_m": 2.0,
                "coverage": 0.9,
            },
        ]
        with unittest.mock.patch("collector.app.match_path") as path_hit:
            with unittest.mock.patch(
                "collector.app.match_time_attack_start",
                side_effect=ta_hits,
            ):
                path_hit.return_value = {
                    "matched": True,
                    "track": "Autodromo Nazionale Monza Junior Course",
                    "distance_m": 4.0,
                    "coverage": 0.8,
                    "path_points": 40,
                }
                state.handle_packet(_blank_packet(lap_number=0, last_lap=0.0))
                state.handle_packet(_blank_packet(lap_number=1, last_lap=110.48))
                state.handle_packet(_blank_packet(lap_number=2, last_lap=106.99))
        try:
            self.assertEqual(len(state.session_laps), 2)
            self.assertEqual(
                state.session_laps[0].track, "Autodromo Nazionale Monza"
            )
            self.assertEqual(
                state.session_laps[1].track, "Autodromo Nazionale Monza"
            )
            self.assertEqual(state.ta_session_track, "Autodromo Nazionale Monza")
        finally:
            store.close()

    def test_lap1_offset_start_overrides_live_arm_guess(self) -> None:
        tracks = [
            "Autodromo Nazionale Monza",
            "Autodromo Nazionale Monza Junior Course",
        ]
        store = LapStore(Path(self._tmp.name) / "monza-arm.db")
        state = CollectorState(store, tracks)
        state.cloud = self.fake
        state.ta_session_active = True
        state.ta_session_track = "Autodromo Nazionale Monza Junior Course"
        state.track = "Autodromo Nazionale Monza Junior Course"
        with unittest.mock.patch("collector.app.match_path") as path_hit:
            with unittest.mock.patch("collector.app.match_time_attack_start") as ta_hit:
                path_hit.return_value = {
                    "matched": True,
                    "track": "Autodromo Nazionale Monza Junior Course",
                    "distance_m": 4.0,
                    "coverage": 0.8,
                    "path_points": 40,
                }
                ta_hit.return_value = {
                    "matched": True,
                    "track": "Autodromo Nazionale Monza",
                    "variant": "slot-1",
                    "distance_m": 1.5,
                    "coverage": 0.95,
                }
                state.handle_packet(_blank_packet(lap_number=0, last_lap=0.0))
                state.handle_packet(_blank_packet(lap_number=1, last_lap=110.48))
        try:
            self.assertEqual(
                state.session_laps[0].track, "Autodromo Nazionale Monza"
            )
            self.assertEqual(state.ta_session_track, "Autodromo Nazionale Monza")
        finally:
            store.close()


class SharedPitLayoutWindowTests(unittest.TestCase):
    def test_brands_hatch_uses_longer_layout_window(self) -> None:
        self.assertEqual(layout_meters_for("Brands Hatch Circuit"), 2000.0)
        self.assertEqual(layout_meters_for("Brands Hatch Indy Circuit"), 2000.0)
        self.assertEqual(layout_meters_for("Autodromo Nazionale Monza"), 800.0)
        self.assertEqual(layout_meters_for("Albert Park"), 180.0)


if __name__ == "__main__":
    unittest.main()
