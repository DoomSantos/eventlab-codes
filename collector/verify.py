"""Classify Albert Park captures: track match + clean/paused/rewound."""

from __future__ import annotations

import json
import math
from pathlib import Path

from .integrity import classify_integrity, meaningful_jumps
from .paths import project_root

ROOT = project_root()
FINGERPRINT = ROOT / "data" / "fingerprints" / "albert-park.json"
TA_START_FINGERPRINT = ROOT / "data" / "fingerprints" / "albert-park-time-attack-start.json"
CAPTURE_DIR = project_root() / "collector" / "captures" / "albert-park"

# Live laps can be slightly short of full-reference coverage; keep verify script strict.
LIVE_COVERAGE_THRESHOLD = 0.45
LIVE_MATCH_THRESHOLD_M = 10.0

_fingerprint_cache: dict | None = None
_ta_start_cache: dict | None = None


def load_fingerprint() -> dict:
    global _fingerprint_cache
    if _fingerprint_cache is None:
        _fingerprint_cache = json.loads(FINGERPRINT.read_text(encoding="utf-8"))
    return _fingerprint_cache


def load_ta_start_fingerprint() -> dict:
    global _ta_start_cache
    if _ta_start_cache is None:
        if not TA_START_FINGERPRINT.is_file():
            raise FileNotFoundError(f"Missing TA start fingerprint: {TA_START_FINGERPRINT}")
        _ta_start_cache = json.loads(TA_START_FINGERPRINT.read_text(encoding="utf-8"))
    return _ta_start_cache


def clear_fingerprint_cache() -> None:
    global _fingerprint_cache, _ta_start_cache
    _fingerprint_cache = None
    _ta_start_cache = None


def _as_points(path: list[dict] | tuple) -> list[dict]:
    points: list[dict] = []
    for p in path:
        if isinstance(p, dict):
            points.append({"x": float(p["x"]), "z": float(p["z"])})
        else:
            points.append({"x": float(p.x), "z": float(p.z)})
    return points


def start_segment(path: list[dict], meters: float) -> list[dict]:
    if not path:
        return []
    out = [path[0]]
    traveled = 0.0
    for a, b in zip(path, path[1:]):
        traveled += math.hypot(b["x"] - a["x"], b["z"] - a["z"])
        out.append(b)
        if traveled >= meters:
            break
    return out


def downsample(path: list[dict], step_m: float = 8.0) -> list[dict]:
    if not path:
        return []
    out = [path[0]]
    last = path[0]
    for p in path[1:]:
        if math.hypot(p["x"] - last["x"], p["z"] - last["z"]) >= step_m:
            out.append(p)
            last = p
    return out


def mean_nearest(query: list[dict], ref: list[dict]) -> float:
    if not query or not ref:
        return float("inf")
    total = 0.0
    for q in query:
        best = min(math.hypot(q["x"] - r["x"], q["z"] - r["z"]) for r in ref)
        total += best
    return total / len(query)


def coverage(query: list[dict], ref: list[dict], radius_m: float = 20.0) -> float:
    if not query or not ref:
        return 0.0
    hit = 0
    for r in ref:
        if any(math.hypot(q["x"] - r["x"], q["z"] - r["z"]) <= radius_m for q in query):
            hit += 1
    return hit / len(ref)


def evaluate_capture(data: dict, fingerprint: dict | None = None) -> dict:
    fingerprint = fingerprint or load_fingerprint()
    ref = fingerprint["points"]
    query = downsample(data.get("path") or [], step_m=float(fingerprint.get("step_m", 8)))
    dist = mean_nearest(query, ref)
    cov = coverage(query, ref)
    track_match = (
        dist <= float(fingerprint.get("match_threshold_m", 8))
        and cov >= float(fingerprint.get("coverage_threshold", 0.55))
    )
    gaps = data.get("gaps") or []
    integrity = classify_integrity(gaps)
    jumps = meaningful_jumps(gaps)
    human = data.get("label")
    # time_attack is a mode tag, not an integrity label
    if human == "time_attack":
        integrity_ok = True
    else:
        expected = "clean" if human == "paused" else human
        integrity_ok = integrity == expected
    return {
        "track_claimed": data.get("track_claimed"),
        "label_human": human,
        "track_match": track_match,
        "track_distance_m": round(dist, 3),
        "track_coverage": round(cov, 3),
        "integrity_auto": integrity,
        "gap_count": len(gaps),
        "max_jump_m": round(max(jumps), 3) if jumps else 0.0,
        "integrity_ok": integrity_ok,
    }


def match_path(
    path: list[dict] | tuple,
    fingerprint: dict | None = None,
    *,
    live: bool = True,
) -> dict:
    """Score a live lap path against the Albert Park fingerprint."""
    fingerprint = fingerprint or load_fingerprint()
    points = _as_points(path)
    ref = fingerprint["points"]
    query = downsample(points, step_m=float(fingerprint.get("step_m", 8)))
    dist = mean_nearest(query, ref)
    cov = coverage(query, ref)
    if live:
        dist_ok = dist <= LIVE_MATCH_THRESHOLD_M
        cov_ok = cov >= LIVE_COVERAGE_THRESHOLD
    else:
        dist_ok = dist <= float(fingerprint.get("match_threshold_m", 8))
        cov_ok = cov >= float(fingerprint.get("coverage_threshold", 0.55))
    matched = bool(query) and dist_ok and cov_ok
    return {
        "track": fingerprint.get("track", "Albert Park"),
        "matched": matched,
        "distance_m": round(dist, 3) if dist != float("inf") else None,
        "coverage": round(cov, 3),
        "path_points": len(points),
        "query_points": len(query),
    }


def match_time_attack_start(
    path: list[dict] | tuple,
    fingerprint: dict | None = None,
) -> dict:
    """Detect Albert Park Time Attack via offset-start fingerprint."""
    try:
        fingerprint = fingerprint or load_ta_start_fingerprint()
    except FileNotFoundError as exc:
        return {
            "matched": False,
            "mode": None,
            "track": "Albert Park",
            "error": str(exc),
        }
    points = _as_points(path)
    meters = float(fingerprint.get("start_meters", 180))
    step = float(fingerprint.get("step_m", 4))
    head = start_segment(points, meters)
    query = downsample(head, step_m=step)
    ref = fingerprint["points"]
    # Short start refs use a slightly wider coverage radius.
    dist = mean_nearest(query, ref)
    cov = coverage(query, ref, radius_m=25.0)
    dist_ok = dist <= float(fingerprint.get("match_threshold_m", 20))
    cov_ok = cov >= float(fingerprint.get("coverage_threshold", 0.55))
    matched = bool(query) and dist_ok and cov_ok
    return {
        "matched": matched,
        "mode": "time_attack" if matched else None,
        "track": fingerprint.get("track", "Albert Park"),
        "distance_m": round(dist, 3) if dist != float("inf") else None,
        "coverage": round(cov, 3),
        "path_points": len(points),
        "start_points": len(head),
        "query_points": len(query),
    }


def main() -> None:
    fingerprint = load_fingerprint()
    rows = []
    for path in sorted(CAPTURE_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        result = evaluate_capture(data, fingerprint)
        result["file"] = path.name
        rows.append(result)

    print(f"Fingerprint: {fingerprint['track']} ({len(fingerprint['points'])} pts)")
    print("\n== Captures with gaps ==")
    gap_rows = [r for r in rows if r["gap_count"] > 0]
    correct = 0
    for r in gap_rows:
        mark = "OK" if r["integrity_ok"] else "MISS"
        if r["integrity_ok"]:
            correct += 1
        print(
            f"  {mark} human={r['label_human']:8} auto={r['integrity_auto']:8} "
            f"jump={r['max_jump_m']:7.1f}m gaps={r['gap_count']} {r['file'][:40]}"
        )
    if gap_rows:
        print(f"Integrity accuracy on gapped laps: {correct}/{len(gap_rows)}")

    cleans = [r for r in rows if r["label_human"] == "clean"]
    clean_ok = sum(1 for r in cleans if r["track_match"])
    print(f"\nClean track matches: {clean_ok}/{len(cleans)}")
    all_ok = sum(1 for r in rows if r["track_match"])
    print(f"All captures matching Albert Park fingerprint: {all_ok}/{len(rows)}")


if __name__ == "__main__":
    main()
