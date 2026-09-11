"""Quick sanity checks for collector internals (no game required)."""

from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from collector.lap_detect import LapDetector
from collector.packet import PACKET_SIZE, format_lap_time, parse_packet
from collector.store import LapStore


def _blank_packet(**overrides: int | float) -> bytes:
    buf = bytearray(PACKET_SIZE)
    # Defaults: race on, class A (3), PI 699, lap fields
    struct.pack_into("<i", buf, 0, 1)
    struct.pack_into("<I", buf, 4, 1000)
    struct.pack_into("<i", buf, 212, 1234)  # ordinal
    struct.pack_into("<i", buf, 216, 3)  # class A
    struct.pack_into("<i", buf, 220, 699)  # PI
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


if __name__ == "__main__":
    unittest.main()
