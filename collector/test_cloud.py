"""Cloud client tests — never write the real collector/device.json."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from collector.cloud import DeviceConfig, TimingClient, load_device_config, save_device_config
from server.app import make_handler
from server.store import TimingStore


class DeviceConfigFileTests(unittest.TestCase):
    def test_roundtrip_uses_explicit_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "device.json"
            cfg = DeviceConfig(
                api_base="http://127.0.0.1:8787",
                device_token="tok",
                display_name="Racer",
            )
            save_device_config(cfg, path)
            loaded = load_device_config(path)
            self.assertEqual(loaded.display_name, "Racer")
            self.assertTrue(loaded.claimed)


class TimingClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = TimingStore(Path(self._tmp.name) / "t.db")
        self.invite = self.store.create_invite("CLOUD-TEST")
        handler = make_handler(self.store, {"Albert Park"})
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.config_path = Path(self._tmp.name) / "device.json"

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.store.close()
        self._tmp.cleanup()

    def test_claim_saves_only_temp_config(self) -> None:
        client = TimingClient(
            DeviceConfig(api_base=f"http://127.0.0.1:{self.port}"),
            config_path=self.config_path,
        )
        client.claim(invite_code=self.invite, display_name="TempRacer")
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["display_name"], "TempRacer")
        self.assertTrue(data["device_token"])
        # Real repo device file must not be required for this test path
        self.assertEqual(client.config_path, self.config_path)


if __name__ == "__main__":
    unittest.main()
