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
            mode="time_attack",
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
            mode="time_attack",
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
            mode="time_attack",
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
            mode="time_attack",
            client_lap_id="lap-2",
            known_tracks=self.tracks,
        )

        # Clean non-TA lap is stored but excluded from the public TA board
        self.store.insert_lap(
            device=auth,
            track="Albert Park",
            lap_time_s=83.0,
            class_name="A",
            car_pi=699,
            car_ordinal=123,
            integrity="clean",
            mode="",
            client_lap_id="lap-non-ta",
            known_tracks=self.tracks,
        )

        board = self.store.board(track="Albert Park")
        self.assertEqual(len(board), 2)
        self.assertEqual(board[0].lap_time_s, 84.102)
        self.assertEqual(board[0].mode, "time_attack")

        # Second TA lap in same class — leaderboard keeps only the best
        self.store.insert_lap(
            device=auth,
            track="Albert Park",
            lap_time_s=83.5,
            class_name="A",
            car_pi=699,
            car_ordinal=123,
            integrity="clean",
            mode="time_attack",
            client_lap_id="lap-faster",
            known_tracks=self.tracks,
        )
        # Different class keeps its own best
        self.store.insert_lap(
            device=auth,
            track="Albert Park",
            lap_time_s=88.0,
            class_name="R",
            car_pi=998,
            car_ordinal=3211,
            integrity="clean",
            mode="time_attack",
            client_lap_id="lap-r",
            known_tracks=self.tracks,
        )
        lb = self.store.leaderboard(track="Albert Park", window="all")
        self.assertEqual(len(lb), 2)
        self.assertEqual(lb[0].lap_time_s, 83.5)
        self.assertEqual(lb[0].class_name, "A")
        filtered = self.store.leaderboard(
            track="Albert Park", class_name="R", window="all"
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].class_name, "R")

        hist = self.store.history(player="clove")
        self.assertEqual(len(hist), 6)

        self.store.upsert_presence(
            device=auth,
            track="Albert Park",
            class_pi="A 699",
            car="Test Car",
            racing=True,
            mode="time_attack",
        )
        live = self.store.live()
        self.assertEqual(len(live), 1)
        self.assertEqual(live[0].display_name, "Clove")

    def test_live_presence_requires_time_attack_mode(self) -> None:
        invite = self.store.create_invite("PRESENCE-TA")
        device, token = self.store.claim_invite(
            invite_code=invite, display_name="OpenWorld"
        )
        auth = self.store.device_from_token(token)
        assert auth is not None
        self.store.upsert_presence(
            device=auth,
            track="Albert Park",
            class_pi="A 700",
            car="2014 Holden HSV GTS",
            racing=True,
            mode="",
        )
        self.assertEqual(self.store.live(), [])
        self.store.upsert_presence(
            device=auth,
            track="Albert Park",
            class_pi="A 700",
            car="2014 Holden HSV GTS",
            racing=True,
            mode="time_attack",
        )
        live = self.store.live()
        self.assertEqual(len(live), 1)
        self.assertEqual(live[0].display_name, "OpenWorld")
        self.store.upsert_presence(
            device=auth,
            track="Albert Park",
            class_pi="A 700",
            car="2014 Holden HSV GTS",
            racing=False,
            mode="",
        )
        self.assertEqual(self.store.live(), [])

    def test_reclaim_invite_reattaches_same_display_name(self) -> None:
        first = self.store.create_invite("FIRST")
        device, old_token = self.store.claim_invite(
            invite_code=first, display_name="Clove"
        )
        self.store.insert_lap(
            device=device,
            track="Albert Park",
            lap_time_s=84.1,
            class_name="A",
            car_pi=699,
            car_ordinal=1,
            integrity="clean",
            mode="time_attack",
            client_lap_id="keep-me",
            known_tracks=self.tracks,
        )
        extra = self.store.create_invite("NEW-PC")
        with self.assertRaises(ValueError):
            self.store.claim_invite(invite_code=extra, display_name="Clove")

        reclaim, canonical = self.store.create_reclaim_invite("clove")
        self.assertEqual(canonical, "Clove")
        with self.assertRaises(ValueError):
            self.store.claim_invite(invite_code=reclaim, display_name="Other")

        reclaimed, new_token = self.store.claim_invite(
            invite_code=reclaim, display_name="clove"
        )
        self.assertEqual(reclaimed.id, device.id)
        self.assertEqual(reclaimed.display_name, "Clove")
        self.assertIsNone(self.store.device_from_token(old_token))
        auth = self.store.device_from_token(new_token)
        assert auth is not None
        board = self.store.board(mode="time_attack", window="all")
        self.assertEqual(len(board), 1)
        self.assertEqual(board[0].display_name, "Clove")
        players = self.store.list_players()
        self.assertEqual(players[0]["display_name"], "Clove")
        self.assertEqual(players[0]["lap_count"], 1)


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
                "mode": "time_attack",
                "client_lap_id": "c1",
            },
            token=token,
        )
        self.assertEqual(status, 201)
        self.assertTrue(uploaded["on_board"])
        self.assertEqual(uploaded["mode"], "time_attack")

        status, board = self._request("GET", "/v1/board?track=Albert%20Park")
        self.assertEqual(status, 200)
        self.assertEqual(board["mode"], "time_attack")
        self.assertEqual(board["window"], "24h")
        self.assertIn("session", board)
        self.assertEqual(board["session"]["tz"], "AEST")
        self.assertEqual(len(board["laps"]), 1)
        self.assertEqual(board["laps"][0]["player"], "RacerOne")
        self.assertIn("car", board["laps"][0])
        self.assertEqual(board["laps"][0]["mode"], "time_attack")

        status, skipped = self._request(
            "POST",
            "/v1/laps",
            {
                "track": "Albert Park",
                "lap_time_s": 80.0,
                "class_name": "A",
                "car_pi": 700,
                "car_ordinal": 1,
                "integrity": "clean",
                "client_lap_id": "c2",
            },
            token=token,
        )
        self.assertEqual(status, 201)
        self.assertFalse(skipped["on_board"])

        status, board2 = self._request("GET", "/v1/board?track=Albert%20Park")
        self.assertEqual(status, 200)
        self.assertEqual(len(board2["laps"]), 1)

        status, lb = self._request(
            "GET", "/v1/leaderboard?track=Albert%20Park&window=all&class=A"
        )
        self.assertEqual(status, 200)
        self.assertEqual(lb["window"], "all")
        self.assertEqual(len(lb["laps"]), 1)
        self.assertEqual(lb["laps"][0]["class_name"], "A")


class AdminHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = TimingStore(Path(self._tmp.name) / "admin.db")
        invite = self.store.create_invite("ADMIN-INVITE")
        self.store.claim_invite(invite_code=invite, display_name="RacerOne")
        handler = make_handler(
            self.store,
            {
                "Albert Park",
                "Autodromo Nazionale Monza",
                "Autodromo Nazionale Monza Junior Course",
            },
            admin_token="secret-admin",
        )
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

    def test_list_players_and_reclaim_invite(self) -> None:
        status, data = self._request("GET", "/v1/admin/players")
        self.assertEqual(status, 401)

        status, data = self._request(
            "GET", "/v1/admin/players", token="secret-admin"
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["players"][0]["display_name"], "RacerOne")

        status, minted = self._request(
            "POST",
            "/v1/admin/invites",
            {"display_name": "RacerOne"},
            token="secret-admin",
        )
        self.assertEqual(status, 201)
        self.assertTrue(minted["reclaim"])
        self.assertEqual(minted["display_name"], "RacerOne")
        self.assertTrue(minted["invite_code"])

        status, missing = self._request(
            "POST",
            "/v1/admin/invites",
            {"display_name": "Nobody"},
            token="secret-admin",
        )
        self.assertEqual(status, 404)

    def test_admin_retag_laps(self) -> None:
        invite = self.store.create_invite("RETAG-INVITE")
        device, _token = self.store.claim_invite(
            invite_code=invite, display_name="RacerTwo"
        )
        row = self.store.insert_lap(
            device=device,
            track="Autodromo Nazionale Monza Junior Course",
            lap_time_s=104.667,
            class_name="A",
            car_pi=700,
            car_ordinal=1,
            integrity="clean",
            mode="time_attack",
            client_lap_id="retag-1",
            known_tracks={
                "Autodromo Nazionale Monza",
                "Autodromo Nazionale Monza Junior Course",
            },
        )
        status, denied = self._request(
            "POST",
            "/v1/admin/laps",
            {"ids": [row.id], "track": "Autodromo Nazionale Monza"},
        )
        self.assertEqual(status, 401)

        status, data = self._request(
            "POST",
            "/v1/admin/laps",
            {"ids": [row.id], "track": "Autodromo Nazionale Monza"},
            token="secret-admin",
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["laps"][0]["id"], row.id)
        self.assertEqual(data["laps"][0]["track"], "Autodromo Nazionale Monza")
        history = self.store.history(player="RacerTwo", limit=5)
        self.assertEqual(history[0].track, "Autodromo Nazionale Monza")


if __name__ == "__main__":
    unittest.main()
