"""Lap completion detection with path + gap capture for verification research."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from .packet import Telemetry

MIN_LAP_S = 20.0
MAX_LAP_S = 30 * 60.0
STREAM_GAP_S = 0.45
PATH_MIN_INTERVAL_S = 0.2
PATH_MIN_DISTANCE_M = 2.0


@dataclass(frozen=True, slots=True)
class GapEvent:
    duration_s: float
    before_x: float
    before_y: float
    before_z: float
    after_x: float
    after_y: float
    after_z: float
    jump_m: float
    lap_time_before_s: float


@dataclass(frozen=True, slots=True)
class PathSample:
    t_s: float
    x: float
    y: float
    z: float
    speed_mps: float
    lap_time_s: float


@dataclass(frozen=True, slots=True)
class CompletedLap:
    lap_time_s: float
    class_name: str
    car_pi: int
    car_ordinal: int
    lap_number: int
    stream_gaps: int = 0
    suspect_rewind: bool = False
    path: tuple[PathSample, ...] = ()
    gaps: tuple[GapEvent, ...] = ()


def _xz_distance(ax: float, az: float, bx: float, bz: float) -> float:
    return math.hypot(bx - ax, bz - az)


class LapDetector:
    def __init__(self) -> None:
        self._last_lap_number: int | None = None
        self._armed = False
        self._last_packet_at: float | None = None
        self._last_tel: Telemetry | None = None
        self._gaps_this_lap: list[GapEvent] = []
        self._path_this_lap: list[PathSample] = []
        self._lap_started_at: float | None = None
        self._last_path_at: float | None = None
        self._last_path_x: float | None = None
        self._last_path_z: float | None = None
        self._pending_gap_start: float | None = None
        self._pending_gap_before: Telemetry | None = None

    def reset(self) -> None:
        self._last_lap_number = None
        self._armed = False
        self._last_packet_at = None
        self._last_tel = None
        self._gaps_this_lap = []
        self._path_this_lap = []
        self._lap_started_at = None
        self._last_path_at = None
        self._last_path_x = None
        self._last_path_z = None
        self._pending_gap_start = None
        self._pending_gap_before = None

    def _begin_lap_segment(self, tel: Telemetry, now: float) -> None:
        self._gaps_this_lap = []
        self._path_this_lap = []
        self._lap_started_at = now
        self._last_path_at = None
        self._last_path_x = None
        self._last_path_z = None
        self._pending_gap_start = None
        self._pending_gap_before = None
        self._maybe_sample_path(tel, now, force=True)

    def _maybe_sample_path(self, tel: Telemetry, now: float, *, force: bool = False) -> None:
        if self._lap_started_at is None:
            return
        if not force and self._last_path_at is not None:
            dt = now - self._last_path_at
            dist = 0.0
            if self._last_path_x is not None and self._last_path_z is not None:
                dist = _xz_distance(
                    self._last_path_x, self._last_path_z, tel.position_x, tel.position_z
                )
            if dt < PATH_MIN_INTERVAL_S and dist < PATH_MIN_DISTANCE_M:
                return
        self._path_this_lap.append(
            PathSample(
                t_s=round(now - self._lap_started_at, 3),
                x=tel.position_x,
                y=tel.position_y,
                z=tel.position_z,
                speed_mps=tel.speed_mps,
                lap_time_s=tel.current_lap,
            )
        )
        self._last_path_at = now
        self._last_path_x = tel.position_x
        self._last_path_z = tel.position_z

    def _close_pending_gap(self, tel: Telemetry, now: float) -> None:
        if self._pending_gap_start is None or self._pending_gap_before is None:
            return
        before = self._pending_gap_before
        duration = now - self._pending_gap_start
        jump = _xz_distance(
            before.position_x, before.position_z, tel.position_x, tel.position_z
        )
        self._gaps_this_lap.append(
            GapEvent(
                duration_s=round(duration, 3),
                before_x=before.position_x,
                before_y=before.position_y,
                before_z=before.position_z,
                after_x=tel.position_x,
                after_y=tel.position_y,
                after_z=tel.position_z,
                jump_m=round(jump, 3),
                lap_time_before_s=round(before.current_lap, 3),
            )
        )
        self._pending_gap_start = None
        self._pending_gap_before = None

    def feed(self, tel: Telemetry) -> CompletedLap | None:
        now = time.monotonic()

        # Do not hard-reset on IsRaceOn==0: pause/rewind often drop race-on
        # (or stop packets). Keep lap state so we can record the discontinuity.
        if not tel.is_race_on:
            if self._last_tel is not None and self._pending_gap_start is None:
                self._pending_gap_start = self._last_packet_at or now
                self._pending_gap_before = self._last_tel
            self._last_packet_at = now
            return None

        if self._last_packet_at is not None:
            gap = now - self._last_packet_at
            if gap >= STREAM_GAP_S and self._last_tel is not None:
                if self._pending_gap_start is None:
                    self._pending_gap_start = self._last_packet_at
                    self._pending_gap_before = self._last_tel

        if self._pending_gap_start is not None:
            self._close_pending_gap(tel, now)

        self._last_packet_at = now
        self._last_tel = tel

        if self._last_lap_number is None:
            self._last_lap_number = tel.lap_number
            self._armed = True
            self._begin_lap_segment(tel, now)
            return None

        self._maybe_sample_path(tel, now)

        if tel.lap_number > self._last_lap_number:
            prev = self._last_lap_number
            self._last_lap_number = tel.lap_number
            lap_time = tel.last_lap
            gaps = tuple(self._gaps_this_lap)
            path = tuple(self._path_this_lap)
            self._begin_lap_segment(tel, now)
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
                    stream_gaps=len(gaps),
                    suspect_rewind=len(gaps) > 0,
                    path=path,
                    gaps=gaps,
                )
            return None

        if tel.lap_number < self._last_lap_number:
            self._last_lap_number = tel.lap_number
            self._begin_lap_segment(tel, now)
        return None
