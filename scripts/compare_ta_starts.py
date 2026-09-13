"""Compare Time Attack captures vs normal Albert Park cleans."""

from __future__ import annotations

import json
import math
from pathlib import Path

from collector.verify import load_fingerprint, match_path

CAP = Path(__file__).resolve().parent.parent / "collector" / "captures" / "albert-park"


def start_centroid(path: list[dict], n: int = 25) -> tuple[float, float] | None:
    pts = path[:n]
    if not pts:
        return None
    return sum(p["x"] for p in pts) / len(pts), sum(p["z"] for p in pts) / len(pts)


def start_segment(path: list[dict], meters: float = 150.0) -> list[dict]:
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


def main() -> None:
    fp = load_fingerprint()
    ref = fp["points"]
    ref_c = start_centroid(ref, 20)
    assert ref_c
    print(f"Fingerprint start centroid: {ref_c[0]:.1f}, {ref_c[1]:.1f}")
    print()

    print("=== Normal EventLab cleans ===")
    norms: list[tuple[float, float]] = []
    norm_ds: list[float] = []
    for path in sorted(CAP.glob("*_clean.json"))[:8]:
        data = json.loads(path.read_text(encoding="utf-8"))
        pts = data["path"]
        full = match_path(pts, fp, live=True)
        head = start_segment(pts, 150)
        hc = start_centroid(head, 25)
        assert hc
        dd = math.hypot(hc[0] - ref_c[0], hc[1] - ref_c[1])
        norms.append(hc)
        norm_ds.append(dd)
        print(
            f"{path.name[-34:]:34} dist={full['distance_m']:5.2f} "
            f"cov={full['coverage']:4.0%} start_d={dd:6.1f}m pts={len(pts)}"
        )
    print(f"normal start_d mean={sum(norm_ds)/len(norm_ds):.1f}m")
    print()

    print("=== Time Attack labeled ===")
    tas: list[tuple[float, float]] = []
    ta_ds: list[float] = []
    files = sorted(CAP.glob("*_time_attack.json"))
    if not files:
        raise SystemExit("No time_attack captures found")
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        pts = data["path"]
        full = match_path(pts, fp, live=True)
        head = start_segment(pts, 150)
        hc = start_centroid(head, 25)
        assert hc
        dd = math.hypot(hc[0] - ref_c[0], hc[1] - ref_c[1])
        p0 = pts[0]
        nearest = min(math.hypot(p0["x"] - r["x"], p0["z"] - r["z"]) for r in ref)
        tas.append(hc)
        ta_ds.append(dd)
        print(
            f"{path.name[-40:]:40} time={data.get('lap_time')} "
            f"dist={full['distance_m']:5.2f} cov={full['coverage']:4.0%} "
            f"start_d={dd:6.1f}m first_to_FP={nearest:5.1f}m pts={len(pts)} "
            f"gaps={data.get('stream_gaps')}"
        )
    print(f"TA start_d mean={sum(ta_ds)/len(ta_ds):.1f}m")
    print()

    nx = sum(c[0] for c in norms) / len(norms)
    nz = sum(c[1] for c in norms) / len(norms)
    tx = sum(c[0] for c in tas) / len(tas)
    tz = sum(c[1] for c in tas) / len(tas)
    cluster = math.hypot(tx - nx, tz - nz)
    ta_spread = [
        math.hypot(c[0] - tx, c[1] - tz) for c in tas
    ]
    print(f"Normal start cluster: {nx:.1f}, {nz:.1f}")
    print(f"TA start cluster:     {tx:.1f}, {tz:.1f}")
    print(f"Distance between clusters: {cluster:.1f} m")
    print(f"TA internal spread max/mean: {max(ta_spread):.1f}/{sum(ta_spread)/len(ta_spread):.1f} m")


if __name__ == "__main__":
    main()
