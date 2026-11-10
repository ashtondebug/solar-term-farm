"""Shared fake device client for MCP tests."""

from __future__ import annotations

import copy
from typing import Any


def sample_state() -> dict[str, Any]:
    return {
        "device": {
            "name": "AgriVerse",
            "version": "0.1.0",
            "now": 1000,
            "now_local": "2026-11-09T18:00:00+08:00",
            "time_synced": True,
            "uptime_s": 123,
        },
        "sensors": {
            "air_temp": {"value": 24.5, "unit": "C", "valid": True, "ts": 995, "error": None},
            "air_humidity": {"value": 63.0, "unit": "%", "valid": True, "ts": 995, "error": None},
            "soil": {"value": 41.0, "unit": "%", "valid": True, "ts": 990, "raw": 18000},
            "light": {"value": 12000.0, "unit": "lx", "valid": False, "ts": 900, "error": "stale"},
        },
        "suitability": {"score": 80, "status": "good", "components": {"soil": 70}, "reasons": []},
        "solar_term": {"name": "立冬", "index": 18, "season": "冬季"},
        "irrigation": {
            "mode": "auto",
            "pump": False,
            "state": "idle",
            "remaining_s": 0,
            "max_run_s": 20,
            "threshold": 35.0,
            "history": [{"action": "stop", "ts": 900}],
        },
        "network": {"wifi": "connected", "ip": "192.168.153.234"},
        "config": {
            "irrigation": {"sensor_stale_s": 90, "mode": "auto", "max_run_s": 20},
            "plant": {"profile": "general", "stage": "growth"},
            "security": {"pin": "123456", "require_pin": True},
            "wifi": {"password": "secret"},
        },
        "meta": {"source": "device", "ts": 1000},
    }


class FakeClient:
    def __init__(self):
        self._state = sample_state()
        self.commands = []
        self.configs = []
        self.imports = []

    def state(self):
        return copy.deepcopy(self._state)

    def history(self, range_name="12h"):
        return {"range": range_name, "points": [{"ts": 1000, "soil": 41}]}

    def plant_profiles(self):
        return {"profiles": [{"key": "general", "name": "通用", "builtin": True}], "stages": ["growth"]}

    def config(self):
        return copy.deepcopy(self._state["config"])

    def health(self):
        return {"version": "0.1.0", "uptime_s": 123, "now": 1000}

    def command(self, action, request_id):
        self.commands.append((action, request_id))
        return {"request_id": request_id, "irrigation": {"pump": action == "start"}}

    def update_config(self, payload):
        self.configs.append(payload)
        return copy.deepcopy(self._state["config"])

    def import_profiles(self, payload):
        self.imports.append(payload)
        return {"imported": ["x"], "profiles": [{"key": "x"}]}
