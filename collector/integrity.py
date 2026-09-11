"""Integrity classification from captured UDP gap jumps."""

from __future__ import annotations

PAUSE_JUMP_MAX_M = 8.0
REWIND_JUMP_MIN_M = 25.0
TELEPORT_IGNORE_M = 1500.0


def meaningful_jumps(gaps: list[dict] | tuple) -> list[float]:
    jumps = []
    for g in gaps or []:
        if hasattr(g, "jump_m"):
            jump = float(g.jump_m)
        else:
            jump = float(g.get("jump_m") or 0.0)
        if jump < TELEPORT_IGNORE_M:
            jumps.append(jump)
    return jumps


def classify_integrity(gaps: list | tuple) -> str:
    """Return clean | rewound.

    Pausing creates gaps but no competitive advantage, so pause counts as clean.
    Only clear rewind-scale position jumps are marked rewound.
    """
    jumps = meaningful_jumps(gaps)
    if any(jump >= REWIND_JUMP_MIN_M for jump in jumps):
        return "rewound"
    return "clean"
