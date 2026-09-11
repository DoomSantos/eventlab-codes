"""Analyze Albert Park captures: path continuity + build a simple track fingerprint."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "captures" / "albert-park"


def load_all() -> list[dict]:
    rows = []
    for path in sorted(ROOT.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_file"] = path.name
        rows.append(data)
    return rows


def path_jumps(path: list[dict], threshold_m: float = 15.0) -> list[dict]:
    jumps = []
    for i in range(1, len(path)):
        a, b = path[i - 1], path[i]
        dist = math.hypot(b["x"] - a["x"], b["z"] - a["z"])
        dt = max(b["t_s"] - a["t_s"], 1e-6)
        if dist >= threshold_m:
            jumps.append(
                {
                    "i": i,
                    "dist_m": round(dist, 2),
                    "dt_s": round(dt, 3),
                    "speed_implied": round(dist / dt, 2),
                    "t_s": b["t_s"],
                }
            )
    return jumps


def downsample(path: list[dict], step_m: float = 8.0) -> list[tuple[float, float]]:
    if not path:
        return []
    out = [(path[0]["x"], path[0]["z"])]
    last = out[0]
    for p in path[1:]:
        pt = (p["x"], p["z"])
        if math.hypot(pt[0] - last[0], pt[1] - last[1]) >= step_m:
            out.append(pt)
            last = pt
    return out


def mean_nearest_distance(query: list[tuple[float, float]], ref: list[tuple[float, float]]) -> float:
    if not query or not ref:
        return float("inf")
    total = 0.0
    for qx, qz in query:
        best = min(math.hypot(qx - rx, qz - rz) for rx, rz in ref)
        total += best
    return total / len(query)


def main() -> None:
    rows = load_all()
    print(f"Loaded {len(rows)} captures from {ROOT}")
    by_label: dict[str, list] = defaultdict(list)
    for row in rows:
        by_label[row.get("label", "unknown")].append(row)

    print("\n== Path discontinuity scan (>=15m between samples) ==")
    for label in ("clean", "paused", "rewound"):
        print(f"\n[{label}]")
        for row in by_label[label]:
            jumps = path_jumps(row.get("path") or [])
            pts = len(row.get("path") or [])
            max_jump = max((j["dist_m"] for j in jumps), default=0)
            print(
                f"  pts={pts:4d} jumps={len(jumps):2d} max={max_jump:7.1f}m "
                f"gaps_field={row.get('stream_gaps')} {row['_file'][:36]}"
            )

    cleans = by_label["clean"]
    refs = [downsample(r.get("path") or []) for r in cleans]
    # Median-ish reference: longest clean path downsampled
    ref = max(refs, key=len) if refs else []
    print(f"\n== Track fingerprint vs longest clean ref ({len(ref)} pts) ==")
    scores = []
    for row in rows:
        q = downsample(row.get("path") or [])
        score = mean_nearest_distance(q, ref)
        scores.append((score, row.get("label"), row["_file"]))
    scores.sort()
    for score, label, name in scores:
        print(f"  {score:7.2f}m  {label:8}  {name[:40]}")

    # Compare max jump distributions
    print("\n== Max sample-jump by label ==")
    for label in ("clean", "paused", "rewound"):
        maxima = []
        for row in by_label[label]:
            jumps = path_jumps(row.get("path") or [], threshold_m=5.0)
            maxima.append(max((j["dist_m"] for j in jumps), default=0.0))
        if maxima:
            print(
                f"  {label:8} n={len(maxima)} median_max={sorted(maxima)[len(maxima)//2]:.1f} "
                f"max_of_max={max(maxima):.1f}"
            )


if __name__ == "__main__":
    main()
