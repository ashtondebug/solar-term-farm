"""Configuration for the AgriVerse MCP bridge."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    base_url: str = "http://192.168.153.234"
    pin: str = ""
    allow_control: bool = False
    timeout_s: float = 8.0
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8765

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            base_url=os.environ.get("AGRI_BASE_URL", "http://192.168.153.234").rstrip("/"),
            pin=os.environ.get("AGRI_PIN", ""),
            allow_control=_env_bool("AGRI_ALLOW_CONTROL", False),
            timeout_s=float(os.environ.get("AGRI_TIMEOUT_S", "8")),
            transport=os.environ.get("AGRI_MCP_TRANSPORT", "stdio"),
            host=os.environ.get("AGRI_MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("AGRI_MCP_PORT", "8765")),
        )

    def validate(self) -> None:
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("AGRI_BASE_URL must start with http:// or https://")
        if self.timeout_s <= 0:
            raise ValueError("AGRI_TIMEOUT_S must be positive")
        if self.transport not in ("stdio", "streamable-http"):
            raise ValueError("AGRI_MCP_TRANSPORT must be stdio or streamable-http")
        if not (0 < self.port < 65536):
            raise ValueError("AGRI_MCP_PORT is out of range")
