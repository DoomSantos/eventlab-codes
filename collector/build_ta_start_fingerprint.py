"""Build Albert Park Time Attack offset-start fingerprint from labeled captures."""

from __future__ import annotations

import json
import math
from pathlib import Path

CAPTURE_DIR = Path(__file__).resolve().parent / "captures" / "albert-park"
OUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "fingerprints"
    / "albert-park-time-attack-start.json"
)
START_METERS = 180.0
STEP_M = 4.0


def downsample(path: list[dict], step_m: float = STEP_M) -> list[dict]:
    if not path:
        return []
    out = [{"x": path[0]["x"], "y": path[0].get("y", 0.0), "z": path[0]["z"]}]
    last = out[0]
    for p in path[1:]:
        if math.hypot(p["x"] - last["x"], p["z"] - last["z"]) >= step_m:
            sample = {"x": p["x"], "y": p.get("y", 0.0), "z": p["z"]}
            out.append(sample)
            last = sample
    return out


def start_segment(path: list[dict], meters: float = START_METERS) -> list[dict]:
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


def mean_nearest(query: list[dict], ref: list[dict]) -> float:
    if not query or not ref:
        return float("inf")
    total = 0.0
    for q in query:
        best = min(math.hypot(q["x"] - r["x"], q["z"] - r["z"]) for r in ref)
        total += best
    return total / len(query)


def coverage(query: list[dict], ref: list[dict], radius_m: float = 25.0) -> float:
    if not query or not ref:
        return 0.0
    hit = 0
    for r in ref:
        if any(math.hypot(q["x"] - r["x"], q["z"] - r["z"]) <= radius_m for q in query):
            hit += 1
    return hit / len(ref)


def main() -> None:
    starts: list[tuple[dict, list[dict]]] = []
    for path in sorted(CAPTURE_DIR.glob("*_time_attack.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("label") != "time_attack" or not data.get("path"):
            continue
        seg = start_segment(data["path"], START_METERS)
        if len(seg) < 10:
            continue
        starts.append((data, seg))

    if len(starts) < 3:
        raise SystemExit(f"Need at least 3 time_attack captures, found {len(starts)}")

    # Longest start segment as reference polyline.
    best_data, best_seg = max(starts, key=lambda t: len(t[1]))
    ref = downsample(best_seg, step_m=STEP_M)

    scores = []
    for _data, seg in starts:
        q = downsample(seg, step_m=STEP_M)
        scores.append(mean_nearest(q, ref))

    payload = {
        "schema": 1,
        "track": "Albert Park",
        "mode": "time_attack",
        "kind": "offset_start",
        "source_laps": len(starts),
        "reference_file": best_data.get("created_at"),
        "start_meters": START_METERS,
        "step_m": STEP_M,
        "match_threshold_m": 20.0,
        "coverage_threshold": 0.55,
        "self_score_mean_m": round(sum(scores) / len(scores), 3),
        "self_score_max_m": round(max(scores), 3),
        "points": [
            {"x": round(p["x"], 3), "y": round(p["y"], 3), "z": round(p["z"], 3)}
            for p in ref
        ],
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(ref)} pts from {len(starts)} TA starts)")
    print(
        f"Self-match mean={payload['self_score_mean_m']}m "
        f"max={payload['self_score_max_m']}m"
    )

    print("\nScore TA starts:")
    for path in sorted(CAPTURE_DIR.glob("*_time_attack.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        q = downsample(start_segment(data.get("path") or []), step_m=STEP_M)
        dist = mean_nearest(q, ref)
        cov = coverage(q, ref)
        matched = dist <= payload["match_threshold_m"] and cov >= payload["coverage_threshold"]
        print(
            f"  TA   dist={dist:5.2f}m cov={cov:4.0%} "
            f"{'MATCH' if matched else 'miss ':5} {path.name[-40:]}"
        )

    print("\nScore normal cleans (should miss):")
    for path in sorted(CAPTURE_DIR.glob("*_clean.json"))[:8]:
        data = json.loads(path.read_text(encoding="utf-8"))
        q = downsample(start_segment(data.get("path") or []), step_m=STEP_M)
        dist = mean_nearest(q, ref)
        cov = coverage(q, ref)
        matched = dist <= payload["match_threshold_m"] and cov >= payload["coverage_threshold"]
        print(
            f"  clean dist={dist:5.2f}m cov={cov:4.0%} "
            f"{'MATCH' if matched else 'miss ':5} {path.name[-40:]}"
        )


if __name__ == "__main__":
    main()
