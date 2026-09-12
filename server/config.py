"""Runtime config for the timing API (CLI + environment)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "server" / "timing.db"


@dataclass(frozen=True, slots=True)
class ServerConfig:
    host: str
    port: int
    db_path: Path
    cors_origins: tuple[str, ...]


def _parse_cors(raw: str) -> tuple[str, ...]:
    return tuple(part.strip().rstrip("/") for part in raw.split(",") if part.strip())


def load_server_config(
    *,
    host: str | None = None,
    port: int | None = None,
    db: Path | None = None,
    cors: str | None = None,
) -> ServerConfig:
    """Merge CLI overrides with environment.

    Env:
      PORT / TIMING_PORT — listen port (cloud hosts usually set PORT)
      TIMING_HOST — bind address (default 127.0.0.1; 0.0.0.0 when PORT is set)
      TIMING_DB — SQLite path
      TIMING_CORS_ORIGINS — comma-separated allowed Origins (empty = * for local)
    """
    env_port = os.environ.get("PORT") or os.environ.get("TIMING_PORT")
    resolved_port = int(port if port is not None else (env_port or 8787))

    if host is not None:
        resolved_host = host
    elif os.environ.get("TIMING_HOST"):
        resolved_host = os.environ["TIMING_HOST"]
    elif env_port:
        resolved_host = "0.0.0.0"
    else:
        resolved_host = "127.0.0.1"

    if db is not None:
        db_path = Path(db)
    elif os.environ.get("TIMING_DB"):
        db_path = Path(os.environ["TIMING_DB"])
    else:
        db_path = DEFAULT_DB

    cors_raw = cors if cors is not None else os.environ.get("TIMING_CORS_ORIGINS", "")
    return ServerConfig(
        host=resolved_host,
        port=resolved_port,
        db_path=db_path,
        cors_origins=_parse_cors(cors_raw),
    )
