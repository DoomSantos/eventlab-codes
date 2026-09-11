"""Build and test a simple Albert Park path fingerprint from labeled captures."""

from __future__ import annotations

import json
import math
from pathlib import Path

CAPTURE_DIR = Path(__file__).resolve().parent / "captures" / "albert-park"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "fingerprints" / "albert-park.json"


def downsample(path: list[dict], step_m: float = 8.0) -> list[dict]:
    if not path:
        return []
    out = [{"x": path[0]["x"], "y": path[0]["y"], "z": path[0]["z"]}]
    last = out[0]
    for p in path[1:]:
        dist = math.hypot(p["x"] - last["x"], p["z"] - last["z"])
        if dist >= step_m:
            sample = {"x": p["x"], "y": p["y"], "z": p["z"]}
            out.append(sample)
            last = sample
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
    """Fraction of reference points that have a query point nearby."""
    if not query or not ref:
        return 0.0
    hit = 0
    for r in ref:
        if any(math.hypot(q["x"] - r["x"], q["z"] - r["z"]) <= radius_m for q in query):
            hit += 1
    return hit / len(ref)


def main() -> None:
    cleans = []
    for path in sorted(CAPTURE_DIR.glob("*_clean.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("label") == "clean" and data.get("path"):
            cleans.append(data)

    if len(cleans) < 3:
        raise SystemExit(f"Need at least 3 clean captures, found {len(cleans)}")

    # Use the longest clean path as the primary reference polyline.
    best = max(cleans, key=lambda d: len(d.get("path") or []))
    ref = downsample(best["path"], step_m=8.0)

    scores = []
    for data in cleans:
        q = downsample(data.get("path") or [])
        scores.append(mean_nearest(q, ref))

    payload = {
        "schema": 1,
        "track": "Albert Park",
        "source_clean_laps": len(cleans),
        "reference_file": best.get("created_at"),
        "step_m": 8.0,
        "match_threshold_m": 8.0,
        "coverage_threshold": 0.55,
        "clean_self_score_mean_m": round(sum(scores) / len(scores), 3),
        "clean_self_score_max_m": round(max(scores), 3),
        "points": [{"x": round(p["x"], 3), "y": round(p["y"], 3), "z": round(p["z"], 3)} for p in ref],
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(ref)} points from {len(cleans)} clean laps)")
    print(
        f"Clean self-match mean={payload['clean_self_score_mean_m']}m "
        f"max={payload['clean_self_score_max_m']}m"
    )

    print("\nScore all captures:")
    for path in sorted(CAPTURE_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        q = downsample(data.get("path") or [])
        dist = mean_nearest(q, ref)
        cov = coverage(q, ref)
        matched = dist <= payload["match_threshold_m"] and cov >= payload["coverage_threshold"]
        print(
            f"  {data.get('label'):8} dist={dist:5.2f}m cov={cov:4.0%} "
            f"{'MATCH' if matched else 'miss ':5} {path.name[:36]}"
        )


if __name__ == "__main__":
    main()
