"""Timing API store + HTTP smoke tests (no network host required for store)."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from server.app import make_handler
from server.store import TimingStore
from http.server import ThreadingHTTPServer


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = TimingStore(Path(self._tmp.name) / "t.db")
        self.tracks = {"Albert Park"}

    def tearDown(self) -> None:
        self.store.close()
        self._tmp.cleanup()

    def test_claim_upload_board_and_live(self) -> None:
        invite = self.store.create_invite("TEST-INVITE")
        device, token = self.store.claim_invite(
            invite_code=invite, display_name="Clove"
        )
        self.assertTrue(token)
        self.assertEqual(device.display_name, "Clove")

        with self.assertRaises(PermissionError):
            self.store.claim_invite(invite_code=invite, display_name="Other")

        auth = self.store.device_from_token(token)
        assert auth is not None

        clean = self.store.insert_lap(
            device=auth,
            track="Albert Park",
            lap_time_s=84.102,
            class_name="A",
            car_pi=699,
            car_ordinal=123,
            integrity="clean",
            client_lap_id="lap-1",
            known_tracks=self.tracks,
        )
        # Idempotent retry with same client_lap_id
        again = self.store.insert_lap(
            device=auth,
            track="Albert Park",
            lap_time_s=84.102,
            class_name="A",
            car_pi=699,
            car_ordinal=123,
            integrity="clean",
            client_lap_id="lap-1",
            known_tracks=self.tracks,
        )
        self.assertEqual(clean.id, again.id)

        # Different client_lap_id must insert even if similar time
        other = self.store.insert_lap(
            device=auth,
            track="Albert Park",
            lap_time_s=84.200,
            class_name="A",
            car_pi=699,
            car_ordinal=123,
            integrity="clean",
            client_lap_id="lap-1-restart",
            known_tracks=self.tracks,
        )
        self.assertNotEqual(clean.id, other.id)

        self.store.insert_lap(
            device=auth,
            track="Albert Park",
            lap_time_s=90.0,
            class_name="A",
            car_pi=699,
            car_ordinal=123,
            integrity="rewound",
            client_lap_id="lap-2",
            known_tracks=self.tracks,
        )

        board = self.store.board(track="Albert Park")
        self.assertEqual(len(board), 2)
        self.assertEqual(board[0].lap_time_s, 84.102)

        hist = self.store.history(player="clove")
        self.assertEqual(len(hist), 3)

        self.store.upsert_presence(
            device=auth,
            track="Albert Park",
            class_pi="A 699",
            car="Test Car",
            racing=True,
        )
        live = self.store.live()
        self.assertEqual(len(live), 1)
        self.assertEqual(live[0].display_name, "Clove")


class HttpSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = TimingStore(Path(self._tmp.name) / "http.db")
        invite = self.store.create_invite("HTTP-INVITE")
        self.invite = invite
        handler = make_handler(self.store, {"Albert Park"})
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.store.close()
        self._tmp.cleanup()

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        token: str | None = None,
    ) -> tuple[int, dict]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        payload = json.dumps(body).encode() if body is not None else None
        conn.request(method, path, body=payload, headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode()
        conn.close()
        data = json.loads(raw) if raw else {}
        return resp.status, data

    def test_claim_and_board(self) -> None:
        status, claimed = self._request(
            "POST",
            "/v1/claim",
            {"invite_code": self.invite, "display_name": "RacerOne"},
        )
        self.assertEqual(status, 201)
        token = claimed["device_token"]

        status, uploaded = self._request(
            "POST",
            "/v1/laps",
            {
                "track": "Albert Park",
                "lap_time_s": 85.5,
                "class_name": "A",
                "car_pi": 700,
                "car_ordinal": 1,
                "integrity": "clean",
                "client_lap_id": "c1",
            },
            token=token,
        )
        self.assertEqual(status, 201)
        self.assertTrue(uploaded["on_board"])

        status, board = self._request("GET", "/v1/board?track=Albert%20Park")
        self.assertEqual(status, 200)
        self.assertEqual(len(board["laps"]), 1)
        self.assertEqual(board["laps"][0]["player"], "RacerOne")
        self.assertIn("car", board["laps"][0])


if __name__ == "__main__":
    unittest.main()
