"""Build a full-lap track fingerprint (optional soft runway corridors).

Usage:
  python -m collector.build_track_fingerprint --track "Top Gear Test Track"
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPTURE_ROOT = Path(__file__).resolve().parent / "captures"
FINGERPRINT_DIR = ROOT / "data" / "fingerprints"

STEP_M = 8.0
MAX_WALL_LAP_RATIO = 2.5
# Half-corridor for normal sections (metres from centerline).
DEFAULT_CORRIDOR_M = 12.0
# Auto soft-zone when training lateral width exceeds this.
SOFT_WIDTH_TRIGGER_M = 14.0
# Extra metres beyond half training-width so live drivers can run a bit wider.
SOFT_RADIUS_MARGIN_M = 10.0
SOFT_MERGE_GAP_M = 80.0


def _slug(value: str) -> str:
    keep = []
    for ch in value.lower().strip():
        if ch.isalnum():
            keep.append(ch)
        elif ch in {" ", "-", "_"}:
            keep.append("-")
    slug = "".join(keep).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "track"


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


def with_arc(path: list[dict]) -> list[tuple[float, dict]]:
    if not path:
        return []
    out: list[tuple[float, dict]] = [(0.0, path[0])]
    dist = 0.0
    prev = path[0]
    for p in path[1:]:
        dist += math.hypot(p["x"] - prev["x"], p["z"] - prev["z"])
        out.append((dist, p))
        prev = p
    return out


def mean_nearest(query: list[dict], ref: list[dict]) -> float:
    if not query or not ref:
        return float("inf")
    total = 0.0
    for q in query:
        best = min(math.hypot(q["x"] - r["x"], q["z"] - r["z"]) for r in ref)
        total += best
    return total / len(query)


def _load_usable(capture_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(capture_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        label = data.get("label")
        if label not in {"clean", "time_attack"} or not data.get("path"):
            continue
        samples = data["path"]
        wall = float(samples[-1].get("t_s") or 0.0)
        lap = float(data.get("lap_time_s") or 0.0)
        if lap > 0 and wall > lap * MAX_WALL_LAP_RATIO:
            print(f"skip bundled/noisy {path.name} (wall={wall:.1f}s lap={lap:.1f}s)")
            continue
        rows.append(data)
    return rows


def _corridor_width_profile(
    laps_arc: list[list[tuple[float, dict]]],
    ref_arc: list[tuple[float, dict]],
    step_m: float = 15.0,
) -> list[tuple[float, float]]:
    length = ref_arc[-1][0] if ref_arc else 0.0
    profile: list[tuple[float, float]] = []
    station = 0.0
    while station < length - 40:
        window = [(d, p) for d, p in ref_arc if abs(d - station) <= 30]
        if len(window) < 2:
            station += step_m
            continue
        hx = window[-1][1]["x"] - window[0][1]["x"]
        hz = window[-1][1]["z"] - window[0][1]["z"]
        hlen = math.hypot(hx, hz) or 1.0
        hx, hz = hx / hlen, hz / hlen
        px, pz = -hz, hx
        centers: list[tuple[float, float]] = []
        for lap in laps_arc:
            best = None
            best_ad = 1e9
            for dist, p in lap:
                ad = abs(dist - station)
                if ad < best_ad and ad <= 45:
                    best_ad = ad
                    best = (float(p["x"]), float(p["z"]))
            if best:
                centers.append(best)
        if len(centers) >= 3:
            cx = sum(c[0] for c in centers) / len(centers)
            cz = sum(c[1] for c in centers) / len(centers)
            laterals = [(x - cx) * px + (z - cz) * pz for x, z in centers]
            width = max(laterals) - min(laterals)
            profile.append((station, width))
        station += step_m
    return profile


def _soft_zones_from_profile(
    profile: list[tuple[float, float]],
) -> list[dict]:
    wide = [s for s, w in profile if w >= SOFT_WIDTH_TRIGGER_M]
    if not wide:
        return []
    regions: list[tuple[float, float]] = []
    start = prev = wide[0]
    for station in wide[1:]:
        if station - prev > SOFT_MERGE_GAP_M:
            regions.append((start, prev))
            start = station
        prev = station
    regions.append((start, prev))

    zones = []
    for a, b in regions:
        chunk = [w for s, w in profile if a <= s <= b]
        peak = max(chunk) if chunk else SOFT_WIDTH_TRIGGER_M
        # Half-width + margin; floor above default corridor.
        radius = max(DEFAULT_CORRIDOR_M + 2.0, (peak / 2.0) + SOFT_RADIUS_MARGIN_M)
        zones.append(
            {
                "from_m": round(max(0.0, a - 20.0), 1),
                "to_m": round(b + 20.0, 1),
                "radius_m": round(radius, 1),
                "training_width_m": round(peak, 1),
                "note": "Wide training lines (e.g. airport runway straights)",
            }
        )
    return zones


def build_for_track(track_name: str) -> Path:
    slug = _slug(track_name)
    capture_dir = CAPTURE_ROOT / slug
    out_path = FINGERPRINT_DIR / f"{slug}.json"
    if not capture_dir.is_dir():
        raise SystemExit(f"No capture folder: {capture_dir}")

    rows = _load_usable(capture_dir)
    if len(rows) < 3:
        raise SystemExit(f"Need at least 3 clean/time_attack captures, found {len(rows)}")

    best = max(rows, key=lambda d: len(d.get("path") or []))
    ref = downsample(best["path"], step_m=STEP_M)
    ref_arc = with_arc(ref)
    laps_arc = [with_arc(downsample(d["path"], step_m=STEP_M)) for d in rows]
    profile = _corridor_width_profile(laps_arc, ref_arc)
    soft_zones = _soft_zones_from_profile(profile)

    scores = []
    for data in rows:
        q = downsample(data.get("path") or [], step_m=STEP_M)
        scores.append(mean_nearest(q, ref))

    # Soft corridor fingerprints score mean *excess* over local radius.
    match_threshold = 5.0 if soft_zones else 8.0

    payload = {
        "schema": 2 if soft_zones else 1,
        "track": track_name,
        "source_laps": len(rows),
        "reference_file": best.get("created_at"),
        "step_m": STEP_M,
        "match_threshold_m": match_threshold,
        "coverage_threshold": 0.55,
        "corridor_radius_m": DEFAULT_CORRIDOR_M,
        "clean_self_score_mean_m": round(sum(scores) / len(scores), 3),
        "clean_self_score_max_m": round(max(scores), 3),
        "points": [
            {"x": round(p["x"], 3), "y": round(p["y"], 3), "z": round(p["z"], 3)}
            for p in ref
        ],
    }
    if soft_zones:
        payload["soft_zones"] = soft_zones
        print(f"Soft zones ({len(soft_zones)}):")
        for zone in soft_zones:
            print(
                f"  {zone['from_m']}-{zone['to_m']}m  "
                f"radius={zone['radius_m']}m  "
                f"(training width {zone['training_width_m']}m)"
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {out_path} ({len(ref)} pts from {len(rows)} laps; "
        f"legacy_mean={payload['clean_self_score_mean_m']}m "
        f"max={payload['clean_self_score_max_m']}m)"
    )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", required=True, help='Track display name')
    args = parser.parse_args()
    build_for_track(args.track)


if __name__ == "__main__":
    main()
