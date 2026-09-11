"""Export local SQLite laps into data/leaderboard.json for GitHub Pages."""

from __future__ import annotations

import json
from pathlib import Path

from .packet import format_lap_time
from .store import LapStore

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "leaderboard.json"


def export_leaderboard(store: LapStore, out_path: Path = DEFAULT_OUT) -> Path:
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
