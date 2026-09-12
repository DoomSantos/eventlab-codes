"""
Local timing board HTTP API.

Usage:
  python -m server --port 8787
  python -m server --create-invite
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from collector.export_board import car_label, load_car_names
from collector.packet import format_lap_time
from collector.tracks import load_track_names

from .config import load_server_config
from .store import TimingStore

ROOT = Path(__file__).resolve().parent.parent


def _json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    raw = handler.rfile.read(length) if length else b"{}"
    if not raw:
        return {}
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON object required")
    return data


def _bearer(handler: BaseHTTPRequestHandler) -> str | None:
    auth = handler.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        return token or None
    return None


def make_handler(
    store: TimingStore,
    known_tracks: set[str],
    car_names: dict[str, str] | None = None,
    cors_origins: tuple[str, ...] = (),
    admin_token: str = "",
):
    cars = car_names if car_names is not None else load_car_names()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def _apply_cors(self) -> None:
            origin = self.headers.get("Origin", "")
            if not cors_origins:
                self.send_header("Access-Control-Allow-Origin", "*")
            elif origin in cors_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

        def _send(self, code: int, payload: dict | list, *, extra_headers: dict | None = None) -> None:
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._apply_cors()
            if extra_headers:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _error(self, code: int, message: str) -> None:
            self._send(code, {"error": message})

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._apply_cors()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            qs = parse_qs(parsed.query)

            if path == "/health":
                self._send(200, {"ok": True})
                return

            if path == "/v1/board":
                track = (qs.get("track") or [None])[0]
                class_pi = (qs.get("class_pi") or [None])[0]
                try:
                    limit = int((qs.get("limit") or ["500"])[0])
                except ValueError:
                    self._error(400, "invalid limit")
                    return
                rows = store.board(track=track, class_pi=class_pi, limit=limit)
                self._send(
                    200,
                    {
                        "window_h": 24,
                        "mode": "all_clean_laps",
                        "laps": [
                            {
                                "id": r.id,
                                "player": r.display_name,
                                "track": r.track,
                                "lap_time_s": r.lap_time_s,
                                "lap_time": format_lap_time(r.lap_time_s),
                                "class_pi": f"{r.class_name} {r.car_pi}",
                                "car_ordinal": r.car_ordinal,
                                "car": car_label(r.car_ordinal, cars),
                                "submitted_at": r.submitted_at,
                            }
                            for r in rows
                        ],
                    },
                )
                return

            if path == "/v1/live":
                rows = store.live()
                self._send(
                    200,
                    {
                        "racers": [
                            {
                                "player": r.display_name,
                                "track": r.track,
                                "class_pi": r.class_pi,
                                "car": r.car,
                                "updated_at": r.updated_at,
                            }
                            for r in rows
                        ]
                    },
                )
                return

            if path == "/v1/history":
                player = (qs.get("player") or [""])[0]
                if not player.strip():
                    self._error(400, "player required")
                    return
                try:
                    limit = int((qs.get("limit") or ["50"])[0])
                except ValueError:
                    self._error(400, "invalid limit")
                    return
                rows = store.history(player=player, limit=limit)
                self._send(
                    200,
                    {
                        "player": player,
                        "laps": [
                            {
                                "id": r.id,
                                "track": r.track,
                                "lap_time_s": r.lap_time_s,
                                "lap_time": format_lap_time(r.lap_time_s),
                                "class_pi": f"{r.class_name} {r.car_pi}",
                                "integrity": r.integrity,
                                "submitted_at": r.submitted_at,
                            }
                            for r in rows
                        ],
                    },
                )
                return

            self._error(404, "not found")

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            try:
                body = _json_body(self)
            except (json.JSONDecodeError, ValueError) as exc:
                self._error(400, str(exc))
                return

            if path == "/v1/claim":
                invite = str(body.get("invite_code", ""))
                name = str(body.get("display_name", ""))
                try:
                    device, token = store.claim_invite(invite_code=invite, display_name=name)
                except LookupError as exc:
                    self._error(404, str(exc))
                    return
                except PermissionError as exc:
                    self._error(409, str(exc))
                    return
                except ValueError as exc:
                    self._error(400, str(exc))
                    return
                self._send(
                    201,
                    {
                        "display_name": device.display_name,
                        "device_token": token,
                    },
                )
                return

            if path == "/v1/admin/invites":
                if not admin_token:
                    self._error(503, "admin invites disabled")
                    return
                provided = _bearer(self) or str(body.get("admin_token", ""))
                if provided != admin_token:
                    self._error(401, "invalid admin token")
                    return
                custom = body.get("code")
                code = store.create_invite(str(custom) if custom else None)
                self._send(201, {"invite_code": code})
                return

            token = _bearer(self)
            if not token:
                self._error(401, "bearer token required")
                return
            device = store.device_from_token(token)
            if device is None:
                self._error(401, "invalid token")
                return

            if path == "/v1/laps":
                try:
                    row = store.insert_lap(
                        device=device,
                        track=str(body.get("track", "")),
                        lap_time_s=float(body["lap_time_s"]),
                        class_name=str(body.get("class_name", "")),
                        car_pi=int(body.get("car_pi", 0)),
                        car_ordinal=int(body.get("car_ordinal", 0)),
                        integrity=str(body.get("integrity", "clean")),
                        stream_gaps=int(body.get("stream_gaps", 0)),
                        client_lap_id=(
                            str(body["client_lap_id"])
                            if body.get("client_lap_id") is not None
                            else None
                        ),
                        known_tracks=known_tracks,
                    )
                except KeyError:
                    self._error(400, "lap_time_s required")
                    return
                except PermissionError as exc:
                    self._error(429, str(exc))
                    return
                except ValueError as exc:
                    self._error(400, str(exc))
                    return
                self._send(
                    201,
                    {
                        "id": row.id,
                        "player": row.display_name,
                        "track": row.track,
                        "lap_time": format_lap_time(row.lap_time_s),
                        "integrity": row.integrity,
                        "submitted_at": row.submitted_at,
                        "on_board": row.integrity == "clean",
                    },
                )
                return

            if path == "/v1/presence":
                try:
                    row = store.upsert_presence(
                        device=device,
                        track=str(body.get("track", "")),
                        class_pi=str(body.get("class_pi", "")),
                        car=str(body.get("car", "")),
                        racing=bool(body.get("racing", True)),
                    )
                except Exception as exc:  # noqa: BLE001
                    self._error(400, str(exc))
                    return
                self._send(
                    200,
                    {
                        "player": row.display_name,
                        "track": row.track,
                        "class_pi": row.class_pi,
                        "updated_at": row.updated_at,
                    },
                )
                return

            self._error(404, "not found")

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DSR timing board API")
    parser.add_argument("--host", default=None, help="Bind host (default 127.0.0.1 or TIMING_HOST)")
    parser.add_argument("--port", type=int, default=None, help="Port (default 8787 or PORT)")
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument(
        "--cors",
        default=None,
        help="Comma-separated allowed Origins (or TIMING_CORS_ORIGINS). Empty = *",
    )
    parser.add_argument(
        "--create-invite",
        nargs="?",
        const="",
        default=None,
        help="Create an invite code and exit (optional custom code)",
    )
    args = parser.parse_args(argv)

    cfg = load_server_config(host=args.host, port=args.port, db=args.db, cors=args.cors)
    store = TimingStore(cfg.db_path)

    if args.create_invite is not None:
        code = store.create_invite(args.create_invite or None)
        print(code)
        store.close()
        return 0

    tracks = set(load_track_names())
    admin = os.environ.get("TIMING_ADMIN_TOKEN", "").strip()
    handler = make_handler(
        store, tracks, cors_origins=cfg.cors_origins, admin_token=admin
    )
    server = ThreadingHTTPServer((cfg.host, cfg.port), handler)
    cors_note = ",".join(cfg.cors_origins) if cfg.cors_origins else "*"
    print(f"Timing API http://{cfg.host}:{cfg.port}  db={cfg.db_path}  cors={cors_note}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping")
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
