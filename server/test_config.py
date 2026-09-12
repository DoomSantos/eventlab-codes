"""Server config + CORS behaviour."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from server.app import make_handler
from server.config import load_server_config
from server.store import TimingStore


class ConfigTests(unittest.TestCase):
    def test_defaults_local(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            # Keep PATH-ish env minimal; clear TIMING_* and PORT
            cleaned = {
                k: v
                for k, v in os.environ.items()
                if k not in {"PORT", "TIMING_PORT", "TIMING_HOST", "TIMING_DB", "TIMING_CORS_ORIGINS"}
            }
            with mock.patch.dict(os.environ, cleaned, clear=True):
                cfg = load_server_config()
        self.assertEqual(cfg.host, "127.0.0.1")
        self.assertEqual(cfg.port, 8787)
        self.assertEqual(cfg.cors_origins, ())

    def test_port_env_binds_all_interfaces(self) -> None:
        with mock.patch.dict(os.environ, {"PORT": "9000"}, clear=False):
            cfg = load_server_config()
        self.assertEqual(cfg.port, 9000)
        self.assertEqual(cfg.host, "0.0.0.0")

    def test_cors_list(self) -> None:
        cfg = load_server_config(cors="https://doomsantos.github.io, http://127.0.0.1:8080")
        self.assertEqual(
            cfg.cors_origins,
            ("https://doomsantos.github.io", "http://127.0.0.1:8080"),
        )


class CorsHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = TimingStore(Path(self._tmp.name) / "c.db")
        handler = make_handler(
            self.store,
            {"Albert Park"},
            cors_origins=("https://doomsantos.github.io",),
        )
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.store.close()
        self._tmp.cleanup()

    def test_allowed_origin_reflected(self) -> None:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(
            "GET",
            "/health",
            headers={"Origin": "https://doomsantos.github.io"},
        )
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertEqual(
            resp.getheader("Access-Control-Allow-Origin"),
            "https://doomsantos.github.io",
        )
        conn.close()

    def test_unknown_origin_not_star(self) -> None:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/health", headers={"Origin": "https://evil.example"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertIsNone(resp.getheader("Access-Control-Allow-Origin"))
        conn.close()


if __name__ == "__main__":
    unittest.main()
