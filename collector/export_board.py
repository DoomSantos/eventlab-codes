"""Export local SQLite laps into data/leaderboard.json for GitHub Pages."""

from __future__ import annotations

import json
from pathlib import Path

from .packet import format_lap_time
from .paths import project_root
from .store import LapStore

ROOT = project_root()
DEFAULT_OUT = ROOT / "data" / "leaderboard.json"
CARS_JSON = ROOT / "data" / "cars.json"


def load_car_names(path: Path = CARS_JSON) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {str(k): str(v) for k, v in data.items()}


def car_label(car_ordinal: int, car_names: dict[str, str]) -> str:
    name = car_names.get(str(car_ordinal))
    if name:
        return name
    return f"Car #{car_ordinal}"


def export_leaderboard(store: LapStore, out_path: Path = DEFAULT_OUT) -> Path:
    car_names = load_car_names()
    laps = store.all_laps()
    payload = {
        "updated_at": None,
        "entries": [
            {
                "track": lap.track,
                "player": lap.player_name,
                "lap_time_s": round(lap.lap_time_s, 3),
                "lap_time": format_lap_time(lap.lap_time_s),
                "class": lap.class_name,
                "pi": lap.car_pi,
                "class_pi": lap.class_pi_label,
                "car_ordinal": lap.car_ordinal,
                "car": car_label(lap.car_ordinal, car_names),
                "suspect_rewind": bool(lap.suspect_rewind),
                "stream_gaps": lap.stream_gaps,
                "integrity": lap.integrity_label,
                "created_at": lap.created_at,
            }
            for lap in laps
        ],
    }
    if laps:
        payload["updated_at"] = max(lap.created_at for lap in laps)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path
