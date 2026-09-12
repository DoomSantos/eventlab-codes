from __future__ import annotations

import json
from pathlib import Path

from .paths import project_root

TRACKS_JSON = project_root() / "data" / "tracks.json"


def load_track_names(path: Path | None = None) -> list[str]:
    target = path or (project_root() / "data" / "tracks.json")
    data = json.loads(target.read_text(encoding="utf-8"))
    return [t["name"] for t in data.get("tracks", [])]
