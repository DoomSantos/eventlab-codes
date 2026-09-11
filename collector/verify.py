"""Classify Albert Park captures: track match + clean/paused/rewound."""

from __future__ import annotations

import json
import math
from pathlib import Path

from .integrity import classify_integrity, meaningful_jumps

ROOT = Path(__file__).resolve().parent.parent
FINGERPRINT = ROOT / "data" / "fingerprints" / "albert-park.json"
CAPTURE_DIR = ROOT / "collector" / "captures" / "albert-park"


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


def load_fingerprint() -> dict:
    return json.loads(FINGERPRINT.read_text(encoding="utf-8"))


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
    return {
        "track_claimed": data.get("track_claimed"),
        "label_human": data.get("label"),
        "track_match": track_match,
        "track_distance_m": round(dist, 3),
        "track_coverage": round(cov, 3),
        "integrity_auto": integrity,
        "gap_count": len(gaps),
        "max_jump_m": round(max(jumps), 3) if jumps else 0.0,
        "integrity_ok": integrity == data.get("label"),
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
