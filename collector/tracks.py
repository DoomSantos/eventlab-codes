from __future__ import annotations

import json
from pathlib import Path

from .paths import project_root

TRACKS_JSON = project_root() / "data" / "tracks.json"
TA_TRACKS_JSON = project_root() / "data" / "time-attack-tracks.json"
TA_CODES_JSON = project_root() / "data" / "time-attack-codes.json"


def _append_name(names: list[str], seen: set[str], name: str) -> None:
    cleaned = name.strip()
    if cleaned and cleaned not in seen:
        names.append(cleaned)
        seen.add(cleaned)


def load_track_names(path: Path | None = None) -> list[str]:
    """Catalogue names plus Time Attack tracks (even before public unveil)."""
    target = path or TRACKS_JSON
    data = json.loads(target.read_text(encoding="utf-8"))
    names = [t["name"] for t in data.get("tracks", [])]
    seen = set(names)
    if TA_TRACKS_JSON.is_file():
        try:
            listed = json.loads(TA_TRACKS_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            listed = {}
        for item in listed.get("tracks") or []:
            if isinstance(item, str):
                _append_name(names, seen, item)
            elif isinstance(item, dict):
                _append_name(names, seen, str(item.get("name") or ""))
    if TA_CODES_JSON.is_file():
        try:
            staged = json.loads(TA_CODES_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            staged = {}
        for event in staged.get("events") or []:
            _append_name(names, seen, str(event.get("track") or ""))
    return names
