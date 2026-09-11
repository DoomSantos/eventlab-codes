"""
PC collector for FH6 EventLab lap times.

Usage:
  python -m collector --port 9876 --web-port 8765

Then in FH6: Settings → HUD and Gameplay → Data Out ON
  IP = this PC's LAN IP (or 127.0.0.1 if same machine)
  Port = 9876

Open http://127.0.0.1:8765
"""

from __future__ import annotations

import argparse
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .export_board import DEFAULT_OUT, export_leaderboard
from .lap_detect import CompletedLap, LapDetector
from .packet import PACKET_SIZE, format_lap_time, parse_packet
from .store import LapStore
from .tracks import load_track_names

STATIC_DIR = Path(__file__).resolve().parent / "static"


class CollectorState:
    def __init__(self, store: LapStore, tracks: list[str]) -> None:
        self.store = store
        self.tracks = tracks
        self.player_name = ""
        self.track = tracks[0] if tracks else ""
        self.detector = LapDetector()
        self.pending: list[CompletedLap] = []
        self.live = None
        self.packets_per_sec = 0
        self._packet_count = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def _pending_payload(self, lap: CompletedLap) -> dict:
        return {
            "lap_time_s": lap.lap_time_s,
            "lap_time": format_lap_time(lap.lap_time_s),
            "class_name": lap.class_name,
            "car_pi": lap.car_pi,
            "class_pi": f"{lap.class_name} {lap.car_pi}",
            "car_ordinal": lap.car_ordinal,
            "lap_number": lap.lap_number,
        }

    def snapshot(self) -> dict:
        with self._lock:
            pending = self._pending_payload(self.pending[0]) if self.pending else None
            live = None
            if self.live:
                live = {
                    "class_pi": self.live.class_pi_label,
                    "lap_number": self.live.lap_number,
                    "current_lap": format_lap_time(self.live.current_lap),
                    "best_lap": format_lap_time(self.live.best_lap),
                    "is_race_on": self.live.is_race_on,
                }
            laps = [
                {
                    "track": lap.track,
                    "player_name": lap.player_name,
                    "lap_time": format_lap_time(lap.lap_time_s),
                    "class_pi": lap.class_pi_label,
                }
                for lap in self.store.all_laps()
            ]
            return {
                "player_name": self.player_name,
                "track": self.track,
                "tracks": self.tracks,
                "pending": pending,
                "pending_count": len(self.pending),
                "live": live,
                "laps": laps,
                "packets_per_sec": self.packets_per_sec,
            }

    def handle_packet(self, data: bytes) -> None:
        tel = parse_packet(data)
        if tel is None:
            return
        with self._lock:
            self._packet_count += 1
            self.live = tel
            completed = self.detector.feed(tel)
            if completed:
                self.pending.append(completed)

    def tick_rates(self) -> None:
        with self._lock:
            self.packets_per_sec = self._packet_count
            self._packet_count = 0

    def set_settings(self, player_name: str, track: str) -> None:
        with self._lock:
            self.player_name = player_name.strip()
            if track in self.tracks:
                self.track = track

    def accept_pending(self, player_name: str | None = None, track: str | None = None) -> dict:
        with self._lock:
            if player_name is not None:
                self.player_name = player_name.strip()
            if track is not None and track in self.tracks:
                self.track = track

            if not self.pending:
                return {"ok": False, "error": "No pending lap"}
            if not self.player_name:
                return {
                    "ok": False,
                    "error": "Enter a display name above, then click Save lap again",
                }
            if not self.track:
                return {"ok": False, "error": "Select a track first"}

            lap = self.pending.pop(0)
            record, improved = self.store.upsert_best(
                track=self.track,
                player_name=self.player_name,
                lap_time_s=lap.lap_time_s,
                class_name=lap.class_name,
                car_pi=lap.car_pi,
                car_ordinal=lap.car_ordinal,
            )
            return {
                "ok": True,
                "improved": improved,
                "lap_time": format_lap_time(record.lap_time_s),
                "class_pi": record.class_pi_label,
                "pending_count": len(self.pending),
            }

    def discard_pending(self) -> dict:
        with self._lock:
            if self.pending:
                self.pending.pop(0)
            return {"ok": True, "pending_count": len(self.pending)}


def make_handler(state: CollectorState):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            if self.path.startswith("/api/"):
                return
            super().log_message(fmt, *args)

        def _json(self, code: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")

        def do_GET(self) -> None:  # noqa: N802
            try:
                path = urlparse(self.path).path
                if path == "/api/state":
                    self._json(200, state.snapshot())
                    return
                if path in ("/", "/index.html"):
                    self._file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
                    return
                self._json(404, {"error": "Not found"})
            except Exception as exc:  # noqa: BLE001
                print(f"GET error: {exc!r}")
                try:
                    self._json(500, {"error": str(exc)})
                except Exception:
                    pass

        def do_POST(self) -> None:  # noqa: N802
            try:
                path = urlparse(self.path).path
                try:
                    data = self._read_json()
                except json.JSONDecodeError:
                    self._json(400, {"error": "Invalid JSON"})
                    return

                if path == "/api/settings":
                    state.set_settings(data.get("player_name", ""), data.get("track", ""))
                    self._json(200, {"ok": True})
                    return
                if path == "/api/pending/accept":
                    result = state.accept_pending(
                        player_name=data.get("player_name"),
                        track=data.get("track"),
                    )
                    self._json(200 if result.get("ok") else 400, result)
                    return
                if path == "/api/pending/discard":
                    result = state.discard_pending()
                    self._json(200, result)
                    return
                if path == "/api/export":
                    out = export_leaderboard(state.store, DEFAULT_OUT)
                    self._json(
                        200,
                        {
                            "ok": True,
                            "path": str(out),
                            "count": len(state.store.all_laps()),
                        },
                    )
                    return
                self._json(404, {"error": "Not found"})
            except Exception as exc:  # noqa: BLE001
                print(f"POST error: {exc!r}")
                try:
                    self._json(500, {"error": str(exc)})
                except Exception:
                    pass

        def _file(self, file_path: Path, content_type: str) -> None:
            if not file_path.is_file():
                self._json(404, {"error": "Missing UI file"})
                return
            body = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def udp_loop(state: CollectorState, host: str, port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    sock.settimeout(0.5)
    print(f"UDP listening on {host}:{port}")
    while not state._stop.is_set():
        try:
            data, _addr = sock.recvfrom(4096)
        except socket.timeout:
            continue
        except OSError:
            break
        if len(data) == PACKET_SIZE:
            state.handle_packet(data)
    sock.close()


def rate_loop(state: CollectorState) -> None:
    while not state._stop.is_set():
        time.sleep(1)
        state.tick_rates()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FH6 EventLab lap collector")
    parser.add_argument("--host", default="0.0.0.0", help="UDP bind host")
    parser.add_argument("--port", type=int, default=9876, help="UDP Data Out port")
    parser.add_argument("--web-host", default="127.0.0.1", help="Local UI host")
    parser.add_argument("--web-port", type=int, default=8765, help="Local UI port")
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Export SQLite laps to data/leaderboard.json and exit",
    )
    args = parser.parse_args(argv)

    tracks = load_track_names()
    store = LapStore()
    state = CollectorState(store, tracks)

    if args.export_only:
        out = export_leaderboard(store, DEFAULT_OUT)
        print(f"Exported {len(store.all_laps())} laps → {out}")
        return 0

    if not tracks:
        print("No tracks found in data/tracks.json")
        return 1

    udp_thread = threading.Thread(
        target=udp_loop, args=(state, args.host, args.port), daemon=True
    )
    rate_thread = threading.Thread(target=rate_loop, args=(state,), daemon=True)
    udp_thread.start()
    rate_thread.start()

    handler = make_handler(state)
    server = ThreadingHTTPServer((args.web_host, args.web_port), handler)
    print(f"Open collector UI: http://{args.web_host}:{args.web_port}")
    print("FH6 -> Settings -> HUD and Gameplay -> Data Out ON")
    print(f"  Data Out IP = this PC   Data Out Port = {args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        state._stop.set()
        server.shutdown()
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
