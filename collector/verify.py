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
TA_START_DIR = ROOT / "data" / "fingerprints"
CAPTURE_DIR = project_root() / "collector" / "captures" / "albert-park"

# Live laps can be slightly short of full-reference coverage; keep verify script strict.
LIVE_COVERAGE_THRESHOLD = 0.45
LIVE_MATCH_THRESHOLD_M = 10.0
# EventLab load onto the offset grid. Lower than integrity's 1500 m ignore
# because Albert Park festival→pits can be ~1300 m.
TA_SPAWN_JUMP_M = 500.0

_fingerprint_cache: dict | None = None
_track_all_cache: list[dict] | None = None
_ta_start_cache: dict | None = None
_ta_start_all_cache: list[dict] | None = None


def load_fingerprint() -> dict:
    global _fingerprint_cache
    if _fingerprint_cache is None:
        _fingerprint_cache = json.loads(FINGERPRINT.read_text(encoding="utf-8"))
    return _fingerprint_cache


def load_all_track_fingerprints() -> list[dict]:
    """Full-lap fingerprints (excludes *-time-attack-start.json)."""
    global _track_all_cache
    if _track_all_cache is None:
        files = sorted(TA_START_DIR.glob("*.json"))
        loaded: list[dict] = []
        for path in files:
            if path.name.endswith("-time-attack-start.json"):
                continue
            loaded.append(json.loads(path.read_text(encoding="utf-8")))
        _track_all_cache = loaded
    return _track_all_cache


def load_ta_start_fingerprint() -> dict:
    global _ta_start_cache
    if _ta_start_cache is None:
        if not TA_START_FINGERPRINT.is_file():
            raise FileNotFoundError(f"Missing TA start fingerprint: {TA_START_FINGERPRINT}")
        _ta_start_cache = json.loads(TA_START_FINGERPRINT.read_text(encoding="utf-8"))
    return _ta_start_cache


def load_all_ta_start_fingerprints() -> list[dict]:
    """All *-time-attack-start.json fingerprints (Albert Park, Monza, …)."""
    global _ta_start_all_cache
    if _ta_start_all_cache is None:
        files = sorted(TA_START_DIR.glob("*-time-attack-start.json"))
        _ta_start_all_cache = [
            json.loads(path.read_text(encoding="utf-8")) for path in files if path.is_file()
        ]
    return _ta_start_all_cache


def clear_fingerprint_cache() -> None:
    global _fingerprint_cache, _track_all_cache, _ta_start_cache, _ta_start_all_cache
    _fingerprint_cache = None
    _track_all_cache = None
    _ta_start_cache = None
    _ta_start_all_cache = None


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


def _teleport_slice_starts(points: list[dict], *, jump_m: float = TA_SPAWN_JUMP_M) -> list[int]:
    """Path indexes that begin a new start window (lap head + post-load teleports)."""
    starts = [0]
    for i in range(1, len(points)):
        gap = math.hypot(points[i]["x"] - points[i - 1]["x"], points[i]["z"] - points[i - 1]["z"])
        if gap >= jump_m:
            starts.append(i)
    return starts


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


def _ref_arc_lengths(ref: list[dict]) -> list[float]:
    if not ref:
        return []
    arcs = [0.0]
    for a, b in zip(ref, ref[1:]):
        arcs.append(arcs[-1] + math.hypot(b["x"] - a["x"], b["z"] - a["z"]))
    return arcs


def corridor_radius_at(arc_m: float, fingerprint: dict) -> float:
    """Local half-corridor: soft runway zones use a wider radius."""
    base = float(fingerprint.get("corridor_radius_m", 8.0))
    for zone in fingerprint.get("soft_zones") or []:
        if float(zone["from_m"]) <= arc_m <= float(zone["to_m"]):
            return float(zone["radius_m"])
    return base


def uses_soft_corridor(fingerprint: dict) -> bool:
    return bool(fingerprint.get("soft_zones")) or "corridor_radius_m" in fingerprint


def mean_corridor_excess(query: list[dict], ref: list[dict], fingerprint: dict) -> float:
    """Mean metres outside the local corridor (0 = fully inside)."""
    if not query or not ref:
        return float("inf")
    arcs = _ref_arc_lengths(ref)
    total = 0.0
    for q in query:
        best_i = 0
        best_d = float("inf")
        for i, r in enumerate(ref):
            d = math.hypot(q["x"] - r["x"], q["z"] - r["z"])
            if d < best_d:
                best_d = d
                best_i = i
        allow = corridor_radius_at(arcs[best_i], fingerprint)
        total += max(0.0, best_d - allow)
    return total / len(query)


def coverage_corridor(query: list[dict], ref: list[dict], fingerprint: dict) -> float:
    if not query or not ref:
        return 0.0
    arcs = _ref_arc_lengths(ref)
    hit = 0
    for i, r in enumerate(ref):
        allow = corridor_radius_at(arcs[i], fingerprint)
        if any(math.hypot(q["x"] - r["x"], q["z"] - r["z"]) <= allow for q in query):
            hit += 1
    return hit / len(ref)


def score_track_fingerprint(
    path: list[dict] | tuple,
    fingerprint: dict,
    *,
    live: bool = True,
) -> dict:
    """Score a lap against one full-lap track fingerprint."""
    points = _as_points(path)
    ref = fingerprint["points"]
    query = downsample(points, step_m=float(fingerprint.get("step_m", 8)))
    soft = uses_soft_corridor(fingerprint)
    if soft:
        dist = mean_corridor_excess(query, ref, fingerprint)
        cov = coverage_corridor(query, ref, fingerprint)
        live_dist_limit = float(fingerprint.get("live_match_threshold_m", 6.0))
        strict_dist_limit = float(fingerprint.get("match_threshold_m", 5.0))
    else:
        dist = mean_nearest(query, ref)
        cov = coverage(query, ref)
        live_dist_limit = LIVE_MATCH_THRESHOLD_M
        strict_dist_limit = float(fingerprint.get("match_threshold_m", 8))
    if live:
        dist_ok = dist <= live_dist_limit
        cov_ok = cov >= LIVE_COVERAGE_THRESHOLD
    else:
        dist_ok = dist <= strict_dist_limit
        cov_ok = cov >= float(fingerprint.get("coverage_threshold", 0.55))
    matched = bool(query) and dist_ok and cov_ok
    return {
        "track": fingerprint.get("track", "Albert Park"),
        "matched": matched,
        "distance_m": round(dist, 3) if dist != float("inf") else None,
        "coverage": round(cov, 3),
        "path_points": len(points),
        "query_points": len(query),
        "soft_corridor": soft,
    }


def evaluate_capture(data: dict, fingerprint: dict | None = None) -> dict:
    fingerprint = fingerprint or load_fingerprint()
    scored = score_track_fingerprint(data.get("path") or [], fingerprint, live=False)
    dist = scored["distance_m"] if scored["distance_m"] is not None else float("inf")
    cov = scored["coverage"]
    track_match = bool(scored["matched"])
    gaps = data.get("gaps") or []
    lap_time_s = data.get("lap_time_s")
    integrity = classify_integrity(gaps, lap_time_s=lap_time_s)
    jumps = meaningful_jumps(gaps, lap_time_s=lap_time_s)
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
    """Score a live lap against full-lap track fingerprint(s).

    If fingerprint is omitted, tries every non-TA fingerprint and returns the
    best match (soft-corridor tracks like Top Gear included).
    """
    if fingerprint is not None:
        return score_track_fingerprint(path, fingerprint, live=live)

    fingerprints = load_all_track_fingerprints()
    if not fingerprints:
        return score_track_fingerprint(path, load_fingerprint(), live=live)

    best: dict | None = None
    for fp in fingerprints:
        scored = score_track_fingerprint(path, fp, live=live)
        if best is None:
            best = scored
            continue
        if scored.get("matched") and not best.get("matched"):
            best = scored
            continue
        if scored.get("matched") == best.get("matched"):
            da = scored.get("distance_m")
            db = best.get("distance_m")
            if da is not None and (db is None or da < db):
                best = scored
    return best or {
        "track": None,
        "matched": False,
        "distance_m": None,
        "coverage": 0.0,
        "path_points": 0,
        "query_points": 0,
    }


def resolve_ta_session_mode(
    *,
    matched: bool,
    lap_number: int,
    session_active: bool,
) -> tuple[str, bool]:
    """Sticky Time Attack mode after an offset-start match.

    The offset start only happens on the first lap of a TA event. Later laps
    start at the normal line, so they inherit mode until the session is cleared.

    Cleared when:
    - a completed lap 1 does not match the offset start (other EventLab), or
    - the live lap counter drops (event quit / restart) — see CollectorState.
    Re-armed only by another offset-start match.
    """
    if matched:
        return "time_attack", True
    if session_active and int(lap_number) > 1:
        return "time_attack", True
    return "", False


def _ta_variant_refs(fingerprint: dict, *, layout: bool = False) -> list[tuple[str, list[dict]]]:
    key = "layout_variants" if layout else "variants"
    variants = fingerprint.get(key) or []
    refs: list[tuple[str, list[dict]]] = []
    for i, variant in enumerate(variants):
        points = variant.get("points") or []
        if points:
            refs.append((str(variant.get("id") or f"slot-{i + 1}"), points))
    if not refs and not layout and fingerprint.get("points"):
        refs.append(("primary", fingerprint["points"]))
    return refs


def score_ta_start_fingerprint(
    path: list[dict] | tuple,
    fingerprint: dict,
    *,
    layout: bool = False,
) -> dict:
    """Score one TA start fingerprint (supports multi-slot variants).

    layout=False uses the short offset-start window (Mode gate).
    layout=True uses layout_meters / layout_variants to separate shared-pit tracks.

    Festival / EventLab load often teleports onto the offset grid after junk
    path. Each 500 m+ jump starts a new window so that still counts.
    """
    points = _as_points(path)
    if layout:
        meters = float(
            fingerprint.get("layout_meters")
            or fingerprint.get("start_meters", 180)
        )
    else:
        meters = float(fingerprint.get("start_meters", 180))
    step = float(fingerprint.get("step_m", 4))
    threshold = float(fingerprint.get("match_threshold_m", 20))
    cov_threshold = float(fingerprint.get("coverage_threshold", 0.55))

    refs = _ta_variant_refs(fingerprint, layout=layout)
    if layout and not refs:
        # No dedicated layout polylines — compare layout-length query to start variants.
        refs = _ta_variant_refs(fingerprint, layout=False)

    best: dict | None = None
    for window_at in _teleport_slice_starts(points):
        head = start_segment(points[window_at:], meters)
        query = downsample(head, step_m=step)
        best_dist = float("inf")
        best_cov = 0.0
        best_variant = None
        matched = False
        for variant_id, ref in refs:
            dist = mean_nearest(query, ref)
            cov = coverage(query, ref, radius_m=25.0)
            ok = bool(query) and dist <= threshold and cov >= cov_threshold
            if ok and (not matched or dist < best_dist):
                matched = True
                best_dist, best_cov, best_variant = dist, cov, variant_id
            elif not matched and dist < best_dist:
                best_dist, best_cov, best_variant = dist, cov, variant_id
        scored = {
            "matched": matched,
            "mode": "time_attack" if matched else None,
            "track": fingerprint.get("track"),
            "variant": best_variant,
            "distance_m": round(best_dist, 3) if best_dist != float("inf") else None,
            "coverage": round(best_cov, 3),
            "path_points": len(points),
            "start_points": len(head),
            "query_points": len(query),
            "layout": layout,
            "meters": meters,
            "window_index": window_at,
        }
        if best is None:
            best = scored
            continue
        if scored.get("matched") and not best.get("matched"):
            best = scored
            continue
        if scored.get("matched") == best.get("matched"):
            da = scored.get("distance_m")
            db = best.get("distance_m")
            if da is not None and (db is None or da < db):
                best = scored
    return best or {
        "matched": False,
        "mode": None,
        "track": fingerprint.get("track"),
        "variant": None,
        "distance_m": None,
        "coverage": 0.0,
        "path_points": len(points),
        "start_points": 0,
        "query_points": 0,
        "layout": layout,
        "meters": meters,
        "window_index": 0,
    }


def match_time_attack_start(
    path: list[dict] | tuple,
    fingerprint: dict | None = None,
) -> dict:
    """Detect Time Attack via offset-start fingerprint(s).

    If fingerprint is omitted, tries every *-time-attack-start.json.
    Shared pit exits (Monza full vs Junior) require the short start *and*
    the longer layout window when a fingerprint defines layout_meters.
    """
    if fingerprint is not None:
        start = score_ta_start_fingerprint(path, fingerprint, layout=False)
        layout_m = float(fingerprint.get("layout_meters") or 0)
        start_m = float(fingerprint.get("start_meters") or 180)
        if start.get("matched") and layout_m > start_m:
            layout = score_ta_start_fingerprint(path, fingerprint, layout=True)
            return layout if layout.get("matched") else {**start, "matched": False, "mode": None}
        return start

    fingerprints = load_all_ta_start_fingerprints()
    if not fingerprints:
        return {
            "matched": False,
            "mode": None,
            "track": None,
            "error": f"No TA start fingerprints in {TA_START_DIR}",
        }

    def _prefer(a: dict, b: dict) -> dict:
        if a.get("matched") and not b.get("matched"):
            return a
        if b.get("matched") and not a.get("matched"):
            return b
        da = a.get("distance_m")
        db = b.get("distance_m")
        if da is None:
            return b
        if db is None:
            return a
        return a if da <= db else b

    confirmed: list[dict] = []
    best_miss: dict | None = None
    layout_passes: list[dict] = []
    for fp in fingerprints:
        start = score_ta_start_fingerprint(path, fp, layout=False)
        layout_m = float(fp.get("layout_meters") or 0)
        start_m = float(fp.get("start_meters") or 180)
        layout = None
        if layout_m > start_m:
            layout = score_ta_start_fingerprint(path, fp, layout=True)
            if layout.get("matched"):
                layout_passes.append(layout)

        if start.get("matched") and layout_m > start_m:
            assert layout is not None
            if layout.get("matched"):
                confirmed.append(layout)
            else:
                rejected = {
                    **start,
                    "matched": False,
                    "mode": None,
                    "layout_rejected": True,
                    "layout_distance_m": layout.get("distance_m"),
                }
                best_miss = rejected if best_miss is None else _prefer(best_miss, rejected)
            continue
        if start.get("matched"):
            confirmed.append(start)
        else:
            best_miss = start if best_miss is None else _prefer(best_miss, start)

    if not confirmed and layout_passes:
        # Start slot matched a sibling track (or narrowly missed), but layout
        # uniquely identifies the correct shared-pit circuit.
        best = layout_passes[0]
        for score in layout_passes[1:]:
            best = _prefer(best, score)
        return best

    if not confirmed:
        return best_miss or {
            "matched": False,
            "mode": None,
            "track": None,
        }

    best = confirmed[0]
    for score in confirmed[1:]:
        best = _prefer(best, score)
    return best


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
