"""Lap completion detection from a live telemetry stream."""

from __future__ import annotations

from dataclasses import dataclass

from .packet import Telemetry

# Sanity bounds for a single EventLab lap (seconds).
MIN_LAP_S = 20.0
MAX_LAP_S = 30 * 60.0


@dataclass(frozen=True, slots=True)
class CompletedLap:
    lap_time_s: float
    class_name: str
    car_pi: int
    car_ordinal: int
    lap_number: int


class LapDetector:
    def __init__(self) -> None:
        self._last_lap_number: int | None = None
        self._armed = False

    def reset(self) -> None:
        self._last_lap_number = None
        self._armed = False

    def feed(self, tel: Telemetry) -> CompletedLap | None:
        if not tel.is_race_on:
            self.reset()
            return None

        if self._last_lap_number is None:
            self._last_lap_number = tel.lap_number
            self._armed = True
            return None

        if tel.lap_number > self._last_lap_number:
            prev = self._last_lap_number
            self._last_lap_number = tel.lap_number
            lap_time = tel.last_lap
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
                )
            return None

        if tel.lap_number < self._last_lap_number:
            # Session restart / discontinuity
            self._last_lap_number = tel.lap_number
        return None
