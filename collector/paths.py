"""Resolve project paths for source runs and frozen collector builds."""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Repo root in dev; folder containing the exe (or _MEIPASS data) when frozen."""
    if getattr(sys, "frozen", False):
        # onedir: data shipped next to the exe; onefile: extracted under _MEIPASS
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled = Path(meipass)
            if (bundled / "data").is_dir():
                return bundled
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def writable_dir() -> Path:
    """Where device.json / local DB may be written (always next to the exe when frozen)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent
