"""
FH6 Data Out packet parser (324-byte Horizon layout).
Source: https://support.forza.net/hc/en-us/articles/51744149102611-Forza-Horizon-6-Data-Out-Documentation
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

PACKET_SIZE = 324

# Byte offsets for fields we use (official FH6 layout).
_OFF_IS_RACE_ON = 0
_OFF_TIMESTAMP = 4
_OFF_CAR_ORDINAL = 212
_OFF_CAR_CLASS = 216
_OFF_CAR_PI = 220
_OFF_POS = 244
_OFF_SPEED = 256
_OFF_BEST_LAP = 296
_OFF_LAST_LAP = 300
_OFF_CURRENT_LAP = 304
_OFF_RACE_TIME = 308
_OFF_LAP_NUMBER = 312
_OFF_RACE_POS = 314
_OFF_GEAR = 319

CLASS_NAMES = ("D", "C", "B", "A", "S1", "S2", "X", "X")


@dataclass(frozen=True, slots=True)
class Telemetry:
    is_race_on: bool
    timestamp_ms: int
    car_ordinal: int
    car_class: int
    car_pi: int
    position_x: float
    position_y: float
    position_z: float
    speed_mps: float
    best_lap: float
    last_lap: float
    current_lap: float
    current_race_time: float
    lap_number: int
    race_position: int
    gear: int

    @property
    def class_name(self) -> str:
        if 0 <= self.car_class < len(CLASS_NAMES):
            return CLASS_NAMES[self.car_class]
        return "?"

    @property
    def class_pi_label(self) -> str:
        return f"{self.class_name} {self.car_pi}"


def parse_packet(data: bytes) -> Telemetry | None:
    if len(data) != PACKET_SIZE:
        return None

    is_race_on = struct.unpack_from("<i", data, _OFF_IS_RACE_ON)[0]
    timestamp_ms = struct.unpack_from("<I", data, _OFF_TIMESTAMP)[0]
    car_ordinal = struct.unpack_from("<i", data, _OFF_CAR_ORDINAL)[0]
    car_class = struct.unpack_from("<i", data, _OFF_CAR_CLASS)[0]
    car_pi = struct.unpack_from("<i", data, _OFF_CAR_PI)[0]
    pos_x, pos_y, pos_z = struct.unpack_from("<fff", data, _OFF_POS)
    speed = struct.unpack_from("<f", data, _OFF_SPEED)[0]
    best_lap = struct.unpack_from("<f", data, _OFF_BEST_LAP)[0]
    last_lap = struct.unpack_from("<f", data, _OFF_LAST_LAP)[0]
    current_lap = struct.unpack_from("<f", data, _OFF_CURRENT_LAP)[0]
    race_time = struct.unpack_from("<f", data, _OFF_RACE_TIME)[0]
    lap_number = struct.unpack_from("<H", data, _OFF_LAP_NUMBER)[0]
    race_position = data[_OFF_RACE_POS]
    gear = data[_OFF_GEAR]

    return Telemetry(
        is_race_on=bool(is_race_on),
        timestamp_ms=timestamp_ms,
        car_ordinal=car_ordinal,
        car_class=car_class,
        car_pi=car_pi,
        position_x=pos_x,
        position_y=pos_y,
        position_z=pos_z,
        speed_mps=speed,
        best_lap=best_lap,
        last_lap=last_lap,
        current_lap=current_lap,
        current_race_time=race_time,
        lap_number=lap_number,
        race_position=race_position,
        gear=gear,
    )


def format_lap_time(seconds: float) -> str:
    if seconds is None or seconds <= 0:
        return "--"
    total_ms = int(round(seconds * 1000))
    minutes, rem_ms = divmod(total_ms, 60_000)
    secs, ms = divmod(rem_ms, 1000)
    if minutes:
        return f"{minutes}:{secs:02d}.{ms:03d}"
    return f"{secs}.{ms:03d}"
