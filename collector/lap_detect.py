"""Lap completion detection from a live telemetry stream."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .packet import Telemetry

# Sanity bounds for a single EventLab lap (seconds).
MIN_LAP_S = 20.0
MAX_LAP_S = 30 * 60.0

# FH6 Data Out pauses during rewind/pause/menus. A gap longer than this
# while IsRaceOn was true is treated as a discontinuity on the current lap.
STREAM_GAP_S = 0.45


@dataclass(frozen=True, slots=True)
class CompletedLap:
    lap_time_s: float
    class_name: str
    car_pi: int
    car_ordinal: int
    lap_number: int
    stream_gaps: int = 0
    suspect_rewind: bool = False


class LapDetector:
    def __init__(self) -> None:
        self._last_lap_number: int | None = None
        self._armed = False
        self._last_packet_at: float | None = None
        self._gaps_this_lap = 0

    def reset(self) -> None:
        self._last_lap_number = None
        self._armed = False
        self._last_packet_at = None
        self._gaps_this_lap = 0

    def feed(self, tel: Telemetry) -> CompletedLap | None:
        now = time.monotonic()

        if not tel.is_race_on:
            self.reset()
            return None

        if self._last_packet_at is not None:
            gap = now - self._last_packet_at
            if gap >= STREAM_GAP_S:
                self._gaps_this_lap += 1
        self._last_packet_at = now

        if self._last_lap_number is None:
            self._last_lap_number = tel.lap_number
            self._armed = True
            self._gaps_this_lap = 0
            return None

        if tel.lap_number > self._last_lap_number:
            prev = self._last_lap_number
            self._last_lap_number = tel.lap_number
            lap_time = tel.last_lap
            gaps = self._gaps_this_lap
            self._gaps_this_lap = 0
            if (
                self._armed
                and MIN_LAP_S <= lap_time <= MAX_LAP_S
                and tel.lap_number >= 1
            ):
                return CompletedLap(
                    lap_time_s=lap_time,
                    class_name=tel.class_name,
                    car_pi=tel.car_pi,
                    car_ordinal=tel.car_ordinal,
                    lap_number=prev + 1 if tel.lap_number == prev + 1 else tel.lap_number,
                    stream_gaps=gaps,
                    suspect_rewind=gaps > 0,
                )
            return None

        if tel.lap_number < self._last_lap_number:
            # Session restart / discontinuity
            self._last_lap_number = tel.lap_number
            self._gaps_this_lap = 0
        return None
