"""HTTP client for the timing board API (claim / upload / presence)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import project_root, writable_dir

DEFAULT_API = "http://127.0.0.1:8787"


def _bundled_default_api() -> str:
    """Prefer data/default-api.json (baked at release), else localhost."""
    path = project_root() / "data" / "default-api.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            base = str(data.get("apiBase") or "").strip().rstrip("/")
            if base:
                return base
        except (OSError, json.JSONDecodeError):
            pass
    return DEFAULT_API


def device_file() -> Path:
    return writable_dir() / "device.json"


@dataclass
class DeviceConfig:
    api_base: str = ""
    device_token: str = ""
    display_name: str = ""

    def __post_init__(self) -> None:
        if not self.api_base:
            self.api_base = _bundled_default_api()

    @property
    def claimed(self) -> bool:
        return bool(self.device_token and self.display_name)

    def to_dict(self) -> dict[str, str]:
        return {
            "api_base": self.api_base.rstrip("/"),
            "device_token": self.device_token,
            "display_name": self.display_name,
        }


def load_device_config(path: Path | None = None) -> DeviceConfig:
    target = path or device_file()
    if not target.is_file():
        return DeviceConfig()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DeviceConfig()
    return DeviceConfig(
        api_base=str(data.get("api_base") or _bundled_default_api()).rstrip("/"),
        device_token=str(data.get("device_token") or ""),
        display_name=str(data.get("display_name") or ""),
    )


def save_device_config(cfg: DeviceConfig, path: Path | None = None) -> None:
    target = path or device_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(cfg.to_dict(), indent=2) + "\n", encoding="utf-8")


class TimingClient:
    def __init__(
        self,
        cfg: DeviceConfig,
        *,
        config_path: Path | None = None,
    ) -> None:
        self.cfg = cfg
        self.config_path = config_path or device_file()

    def set_api_base(self, api_base: str) -> None:
        self.cfg.api_base = api_base.rstrip("/") or _bundled_default_api()

    def save(self) -> None:
        save_device_config(self.cfg, self.config_path)

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        auth: bool = False,
    ) -> dict[str, Any]:
        url = f"{self.cfg.api_base}{path}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if auth:
            if not self.cfg.device_token:
                raise RuntimeError("not claimed — enter an invite code first")
            headers["Authorization"] = f"Bearer {self.cfg.device_token}"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(detail)
                message = payload.get("error") or detail
            except json.JSONDecodeError:
                message = detail or str(exc)
            raise RuntimeError(message) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"timing API unreachable ({self.cfg.api_base}): {exc.reason}"
            ) from exc

    def health(self) -> bool:
        try:
            self._request("GET", "/health")
            return True
        except RuntimeError:
            return False

    def claim(self, *, invite_code: str, display_name: str) -> DeviceConfig:
        data = self._request(
            "POST",
            "/v1/claim",
            {"invite_code": invite_code, "display_name": display_name},
        )
        self.cfg.device_token = str(data["device_token"])
        self.cfg.display_name = str(data["display_name"])
        self.save()
        return self.cfg

    def upload_lap(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/v1/laps", payload, auth=True)

    def presence(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/v1/presence", payload, auth=True)
