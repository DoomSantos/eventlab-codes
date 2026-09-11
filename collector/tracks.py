from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKS_JSON = ROOT / "data" / "tracks.json"


def load_track_names(path: Path = TRACKS_JSON) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [t["name"] for t in data.get("tracks", [])]
