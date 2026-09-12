"""Frozen entrypoint for the DSR Lap Collector desktop build."""

from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path


def _prepare_cwd() -> None:
    if getattr(sys, "frozen", False):
        os.chdir(Path(sys.executable).resolve().parent)


def main() -> int:
    _prepare_cwd()
    # Ensure project packages import when frozen
    from collector.app import main as collector_main

    # Open UI shortly after bind — collector prints the URL; we open default ports.
    host = "127.0.0.1"
    port = 8765
    try:
        webbrowser.open(f"http://{host}:{port}")
    except Exception:
        pass
    return collector_main(
        [
            "--host",
            "0.0.0.0",
            "--port",
            "9876",
            "--web-host",
            host,
            "--web-port",
            str(port),
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
