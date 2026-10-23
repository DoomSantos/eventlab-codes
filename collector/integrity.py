"""Integrity classification from captured UDP gap jumps."""

from __future__ import annotations

PAUSE_JUMP_MAX_M = 8.0
REWIND_JUMP_MIN_M = 25.0
TELEPORT_IGNORE_M = 1500.0
# Standing / countdown / spawn teleports happen with the lap timer still ~0.
START_GRACE_S = 1.0
# Gaps whose timer is past the finished lap are from a prior abandoned attempt.
STALE_AFTER_LAP_S = 0.25
# In-game rewind UI usually resumes within a few seconds (research batch ~3–6s).
REWIND_GAP_DURATION_MIN_S = 1.0
REWIND_GAP_DURATION_MAX_S = 8.0


def _gap_jump(g: object) -> float:
    if hasattr(g, "jump_m"):
        return float(g.jump_m)
    return float(g.get("jump_m") or 0.0)  # type: ignore[union-attr]


def _gap_duration(g: object) -> float:
    if hasattr(g, "duration_s"):
        return float(g.duration_s)
    return float(g.get("duration_s") or 0.0)  # type: ignore[union-attr]


def _gap_lap_time_before(g: object) -> float:
    if hasattr(g, "lap_time_before_s"):
        return float(g.lap_time_before_s)
    return float(g.get("lap_time_before_s") or 0.0)  # type: ignore[union-attr]


def meaningful_jumps(
    gaps: list[dict] | tuple,
    *,
    lap_time_s: float | None = None,
) -> list[float]:
    jumps = []
    for g in gaps or []:
        jump = _gap_jump(g)
        if jump >= TELEPORT_IGNORE_M:
            continue
        t_before = _gap_lap_time_before(g)
        if t_before < START_GRACE_S:
            continue
        if lap_time_s is not None and t_before > float(lap_time_s) + STALE_AFTER_LAP_S:
            continue
        jumps.append(jump)
    return jumps


def is_rewindish_gap(g: object) -> bool:
    """True for short, mid-lap, rewind-scale jumps (not long menu/load gaps)."""
    jump = _gap_jump(g)
    if jump < REWIND_JUMP_MIN_M or jump >= TELEPORT_IGNORE_M:
        return False
    dur = _gap_duration(g)
    if dur < REWIND_GAP_DURATION_MIN_S or dur > REWIND_GAP_DURATION_MAX_S:
        return False
    return _gap_lap_time_before(g) >= START_GRACE_S


def classify_integrity(
    gaps: list | tuple,
    *,
    lap_time_s: float | None = None,
    force_rewound: bool = False,
) -> str:
    """Return clean | rewound.

    Pausing creates gaps but no competitive advantage, so pause counts as clean.
    Only clear rewind-scale position jumps are marked rewound.
    Pre-start spawn teleports and stale prior-attempt gaps are ignored.
    """
    if force_rewound:
        return "rewound"
    jumps = meaningful_jumps(gaps, lap_time_s=lap_time_s)
    if any(jump >= REWIND_JUMP_MIN_M for jump in jumps):
        return "rewound"
    return "clean"
