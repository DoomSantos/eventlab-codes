"""Build Time Attack offset-start fingerprint(s) from labeled captures.

Usage:
  python -m collector.build_ta_start_fingerprint
  python -m collector.build_ta_start_fingerprint --track "Autodromo Nazionale Monza"
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPTURE_ROOT = Path(__file__).resolve().parent / "captures"
FINGERPRINT_DIR = ROOT / "data" / "fingerprints"

START_METERS = 180.0
# When two tracks share a pit exit (Monza full vs Junior), a longer window
# separates layouts after they diverge.
LAYOUT_METERS_DEFAULT = 800.0
# Brands Hatch GP/Indy stay together ~1.4 km; 2 km is past the split.
LAYOUT_METERS_BY_TRACK = {
    "Autodromo Nazionale Monza": LAYOUT_METERS_DEFAULT,
    "Autodromo Nazionale Monza Junior Course": LAYOUT_METERS_DEFAULT,
    "Brands Hatch Circuit": 2000.0,
    "Brands Hatch Indy Circuit": 2000.0,
}
STEP_M = 4.0
CLUSTER_RADIUS_M = 40.0
# Skip abandoned/restart-bundled sessions (wall clock >> lap time).
MAX_WALL_LAP_RATIO = 2.5
# Tracks known to share offset starts need the longer layout window.
SHARED_PIT_LAYOUT_TRACKS = set(LAYOUT_METERS_BY_TRACK)
# Ignore misfiled sibling-layout laps sitting in the wrong capture folder.
MIN_PATH_M_BY_TRACK = {
    "Brands Hatch Circuit": 2800.0,
}


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


def layout_meters_for(track_name: str) -> float:
    if track_name in LAYOUT_METERS_BY_TRACK:
        return LAYOUT_METERS_BY_TRACK[track_name]
    if track_name in SHARED_PIT_LAYOUT_TRACKS:
        return LAYOUT_METERS_DEFAULT
    return START_METERS


def path_length_m(path: list[dict]) -> float:
    total = 0.0
    for a, b in zip(path, path[1:]):
        total += math.hypot(b["x"] - a["x"], b["z"] - a["z"])
    return total


def _cluster_starts(
    starts: list[tuple[dict, list[dict], Path]],
) -> list[list[tuple[dict, list[dict], Path]]]:
    clusters: list[list[tuple[dict, list[dict], Path]]] = []
    for item in starts:
        data, seg, _path = item
        sx, sz = float(seg[0]["x"]), float(seg[0]["z"])
        placed = False
        for cluster in clusters:
            cx = float(cluster[0][1][0]["x"])
            cz = float(cluster[0][1][0]["z"])
            if math.hypot(sx - cx, sz - cz) <= CLUSTER_RADIUS_M:
                cluster.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])
    return clusters


def build_for_track(track_name: str) -> Path:
    slug = _slug(track_name)
    capture_dir = CAPTURE_ROOT / slug
    out_path = FINGERPRINT_DIR / f"{slug}-time-attack-start.json"
    if not capture_dir.is_dir():
        raise SystemExit(f"No capture folder: {capture_dir}")

    starts: list[tuple[dict, list[dict], Path]] = []
    for path in sorted(capture_dir.glob("*_time_attack.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("label") != "time_attack" or not data.get("path"):
            continue
        samples = data["path"]
        min_path = MIN_PATH_M_BY_TRACK.get(track_name)
        if min_path and path_length_m(samples) < min_path:
            print(
                f"skip short/misfiled {path.name} "
                f"(path={path_length_m(samples):.0f}m need>={min_path:.0f}m)"
            )
            continue
        wall = float(samples[-1].get("t_s") or 0.0)
        lap = float(data.get("lap_time_s") or 0.0)
        if lap > 0 and wall > lap * MAX_WALL_LAP_RATIO:
            print(f"skip bundled/noisy {path.name} (wall={wall:.1f}s lap={lap:.1f}s)")
            continue
        seg = start_segment(samples, START_METERS)
        if len(seg) < 10:
            print(f"skip short start segment {path.name} ({len(seg)} pts)")
            continue
        starts.append((data, seg, path))

    if len(starts) < 2:
        raise SystemExit(f"Need at least 2 clean time_attack captures, found {len(starts)}")

    clusters = _cluster_starts(starts)
    variants = []
    for idx, cluster in enumerate(clusters):
        # Prefer longest start polyline inside the cluster.
        best_data, best_seg, best_path = max(cluster, key=lambda t: len(t[1]))
        ref = downsample(best_seg, step_m=STEP_M)
        scores = []
        for _data, seg, _p in cluster:
            q = downsample(seg, step_m=STEP_M)
            scores.append(mean_nearest(q, ref))
        variants.append(
            {
                "id": f"slot-{idx + 1}",
                "source_laps": len(cluster),
                "reference_file": best_data.get("created_at"),
                "reference_capture": best_path.name,
                "start_xz": {
                    "x": round(float(best_seg[0]["x"]), 3),
                    "z": round(float(best_seg[0]["z"]), 3),
                },
                "self_score_mean_m": round(sum(scores) / len(scores), 3),
                "self_score_max_m": round(max(scores), 3),
                "points": [
                    {
                        "x": round(p["x"], 3),
                        "y": round(p["y"], 3),
                        "z": round(p["z"], 3),
                    }
                    for p in ref
                ],
            }
        )

    # Primary points = longest variant (back-compat with single-polyline matcher).
    primary = max(variants, key=lambda v: len(v["points"]))
    layout_meters = layout_meters_for(track_name)
    # Longer layout polylines for shared-pit tracks (disambiguation).
    layout_variants = []
    if layout_meters > START_METERS:
        for idx, cluster in enumerate(clusters):
            best_data, _seg, best_path = max(
                (
                    (
                        data,
                        start_segment(data["path"], layout_meters),
                        path,
                    )
                    for data, _short, path in cluster
                ),
                key=lambda t: len(t[1]),
            )
            layout_seg = start_segment(best_data["path"], layout_meters)
            if len(layout_seg) < 20:
                continue
            layout_variants.append(
                {
                    "id": f"slot-{idx + 1}",
                    "points": [
                        {
                            "x": round(p["x"], 3),
                            "y": round(p.get("y", 0.0), 3),
                            "z": round(p["z"], 3),
                        }
                        for p in downsample(layout_seg, step_m=STEP_M)
                    ],
                }
            )

    payload = {
        "schema": 2,
        "track": track_name,
        "mode": "time_attack",
        "kind": "offset_start",
        "source_laps": len(starts),
        "slot_variants": len(variants),
        "start_meters": START_METERS,
        "layout_meters": layout_meters,
        "step_m": STEP_M,
        "match_threshold_m": 20.0,
        "coverage_threshold": 0.55,
        "points": primary["points"],
        "variants": variants,
    }
    if layout_variants:
        payload["layout_variants"] = layout_variants

    # Keep staged share codes across rebuilds (not public until CD unveil).
    if out_path.is_file():
        try:
            prev = json.loads(out_path.read_text(encoding="utf-8"))
            if prev.get("share_code"):
                payload["share_code"] = prev["share_code"]
            if "share_code_published" in prev:
                payload["share_code_published"] = prev["share_code_published"]
        except json.JSONDecodeError:
            pass
    codes_path = ROOT / "data" / "time-attack-codes.json"
    if codes_path.is_file():
        try:
            staged = json.loads(codes_path.read_text(encoding="utf-8"))
            for event in staged.get("events") or []:
                if event.get("track") == track_name and event.get("code"):
                    payload["share_code"] = str(event["code"])
                    payload["share_code_published"] = bool(staged.get("published"))
                    break
        except json.JSONDecodeError:
            pass

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {out_path} ({len(variants)} slot variant(s), "
        f"{len(starts)} captures, primary {len(primary['points'])} pts)"
    )

    print("\nCross-score (any-variant match):")
    for _data, seg, path in starts:
        q = downsample(seg, step_m=STEP_M)
        best_dist = float("inf")
        best_cov = 0.0
        best_id = ""
        for variant in variants:
            dist = mean_nearest(q, variant["points"])
            cov = coverage(q, variant["points"])
            if dist < best_dist:
                best_dist, best_cov, best_id = dist, cov, variant["id"]
        matched = (
            best_dist <= payload["match_threshold_m"]
            and best_cov >= payload["coverage_threshold"]
        )
        print(
            f"  {'MATCH' if matched else 'miss ':5} dist={best_dist:5.2f}m "
            f"cov={best_cov:4.0%} via {best_id}  {path.name[-42:]}"
        )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--track",
        default="Albert Park",
        help='Track display name (default: "Albert Park")',
    )
    args = parser.parse_args()
    build_for_track(args.track)


if __name__ == "__main__":
    main()
