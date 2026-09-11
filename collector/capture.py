"""Save labeled lap captures for track / rewind research."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .export_board import car_label, load_car_names
from .lap_detect import CompletedLap
from .packet import format_lap_time

ROOT = Path(__file__).resolve().parent.parent
CAPTURE_ROOT = ROOT / "collector" / "captures"

VALID_LABELS = ("clean", "paused", "rewound", "unknown")


def _slug(value: str) -> str:
    keep = []
    for ch in value.lower().strip():
        if ch.isalnum():
            keep.append(ch)
        elif ch in {" ", "-", "_"}:
            keep.append("-")
    slug = "".join(keep).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "track"


def capture_payload(
    *,
    lap: CompletedLap,
    track: str,
    player_name: str,
    label: str,
) -> dict:
    label = label if label in VALID_LABELS else "unknown"
    car_names = load_car_names()
    return {
        "schema": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "track_claimed": track,
        "player_name": player_name,
        "label": label,
        "lap_number": lap.lap_number,
        "lap_time_s": round(lap.lap_time_s, 3),
        "lap_time": format_lap_time(lap.lap_time_s),
        "class_name": lap.class_name,
        "car_pi": lap.car_pi,
        "class_pi": f"{lap.class_name} {lap.car_pi}",
        "car_ordinal": lap.car_ordinal,
        "car": car_label(lap.car_ordinal, car_names),
        "stream_gaps": lap.stream_gaps,
        "suspect_auto": lap.suspect_rewind,
        "path": [
            {
                "t_s": s.t_s,
                "x": round(s.x, 3),
                "y": round(s.y, 3),
                "z": round(s.z, 3),
                "speed_mps": round(s.speed_mps, 3),
                "lap_time_s": round(s.lap_time_s, 3),
            }
            for s in lap.path
        ],
        "gaps": [
            {
                "duration_s": g.duration_s,
                "jump_m": g.jump_m,
                "lap_time_before_s": g.lap_time_before_s,
                "before": {
                    "x": round(g.before_x, 3),
                    "y": round(g.before_y, 3),
                    "z": round(g.before_z, 3),
                },
                "after": {
                    "x": round(g.after_x, 3),
                    "y": round(g.after_y, 3),
                    "z": round(g.after_z, 3),
                },
            }
            for g in lap.gaps
        ],
    }


def save_capture(payload: dict) -> Path:
    track_dir = CAPTURE_ROOT / _slug(str(payload.get("track_claimed", "track")))
    track_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    label = payload.get("label", "unknown")
    path = track_dir / f"{stamp}_{label}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def capture_counts(track: str | None = None) -> dict[str, int]:
    counts = {label: 0 for label in VALID_LABELS}
    if not CAPTURE_ROOT.is_dir():
        return counts
    roots = [CAPTURE_ROOT / _slug(track)] if track else list(CAPTURE_ROOT.glob("*"))
    for folder in roots:
        if not folder.is_dir():
            continue
        for file in folder.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            label = data.get("label", "unknown")
            if label in counts:
                counts[label] += 1
            else:
                counts["unknown"] += 1
    return counts
