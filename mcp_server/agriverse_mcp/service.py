"""High-level AgriVerse operations exposed through MCP.

This module deliberately contains no GPIO access.  All pump operations go
through the device's IrrigationController, which owns the safety envelope.
"""

from __future__ import annotations

import copy
import logging
import time
import uuid
from typing import Any

from .device_client import DeviceClient, DeviceError


AUDIT = logging.getLogger("agriverse.mcp.audit")


SENSOR_LABELS = {
    "air_temp": ("空气温度", "°C"),
    "air_humidity": ("空气湿度", "%"),
    "soil": ("土壤湿度", "%"),
    "light": ("环境光照", "lx"),
}
SENSITIVE_KEYS = {"pin", "password", "wifi_password", "token", "secret", "api_key"}
HISTORY_RANGES = ("12h", "24h", "7d")
CONFIRM_START = "START_IRRIGATION"
CONFIRM_MODE = "SET_MODE"
CONFIRM_THRESHOLD = "SET_THRESHOLD"
CONFIRM_PROFILE = "APPLY_PROFILE"
CONFIRM_IMPORT = "IMPORT_PROFILES"


class ServiceError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return "%s: %s" % (self.code, self.message)


def redact(value: Any, key: str = "") -> Any:
    if key.lower() in SENSITIVE_KEYS:
        return "***"
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class AgriVerseService:
    def __init__(self, client: DeviceClient, allow_control: bool = False):
        self.client = client
        self.allow_control = bool(allow_control)

    # ------------------------------------------------------------------ reads
    def _state(self) -> dict[str, Any]:
        try:
            state = self.client.state()
        except DeviceError:
            raise
        if not isinstance(state, dict):
            raise ServiceError("BAD_DEVICE_STATE", "device returned an invalid state object")
        return state

    @staticmethod
    def _now(state: dict[str, Any]) -> int:
        device = state.get("device") or {}
        now = device.get("now")
        return int(now) if isinstance(now, (int, float)) else int(time.time())

    def _sensor_payload(self, state: dict[str, Any]) -> dict[str, Any]:
        sensors = state.get("sensors") or {}
        now = self._now(state)
        stale_s = int((state.get("config") or {}).get("irrigation", {}).get("sensor_stale_s", 90))
        result: dict[str, Any] = {}
        for name, item in sensors.items():
            if not isinstance(item, dict):
                continue
            reading = copy.deepcopy(item)
            ts = reading.get("ts")
            age_s = max(0, now - int(ts)) if isinstance(ts, (int, float)) else None
            reading["age_s"] = age_s
            reading["stale"] = bool(age_s is None or age_s > stale_s or not reading.get("valid"))
            label, unit = SENSOR_LABELS.get(name, (name, reading.get("unit", "")))
            reading["label"] = label
            reading["unit"] = reading.get("unit") or unit
            result[name] = reading
        return result

    def get_environment(self) -> dict[str, Any]:
        state = self._state()
        sensors = self._sensor_payload(state)
        return {
            "observed_at": state.get("device", {}).get("now_local") or state.get("device", {}).get("now"),
            "source": state.get("meta", {}).get("source"),
            "sensors": sensors,
        }

    def get_state(self) -> dict[str, Any]:
        return redact(self._state())

    def get_sensors(self) -> dict[str, Any]:
        return self.get_environment()

    def get_sensor_status(self) -> dict[str, Any]:
        state = self._state()
        sensors = self._sensor_payload(state)
        return {
            "all_ok": all(item.get("valid") and not item.get("stale") for item in sensors.values()),
            "sensors": sensors,
        }

    def get_suitability(self) -> dict[str, Any]:
        state = self._state()
        return {
            "suitability": state.get("suitability"),
            "plant": (state.get("config") or {}).get("plant"),
            "source": state.get("meta", {}).get("source"),
        }

    def get_solar_term(self) -> dict[str, Any]:
        state = self._state()
        return {
            "solar_term": state.get("solar_term"),
            "time_synced": (state.get("device") or {}).get("time_synced"),
        }

    def get_irrigation_status(self) -> dict[str, Any]:
        state = self._state()
        return {
            "irrigation": state.get("irrigation"),
            "sensors": {
                name: {
                    "value": item.get("value"),
                    "unit": item.get("unit"),
                    "valid": item.get("valid"),
                    "stale": item.get("stale"),
                }
                for name, item in self._sensor_payload(state).items()
            },
        }

    def get_irrigation_history(self, limit: int = 10) -> dict[str, Any]:
        limit = max(1, min(int(limit), 50))
        state = self._state()
        history = (state.get("irrigation") or {}).get("history") or []
        return {"history": history[:limit], "count": min(len(history), limit)}

    def get_history(self, range_name: str = "12h") -> dict[str, Any]:
        if range_name not in HISTORY_RANGES:
            raise ServiceError("BAD_RANGE", "range must be 12h, 24h or 7d")
        return self.client.history(range_name)

    def get_plant_profiles(self) -> dict[str, Any]:
        return self.client.plant_profiles()

    def get_config(self) -> dict[str, Any]:
        return redact(self.client.config())

    def get_health(self) -> dict[str, Any]:
        return self.client.health()

    def diagnose(self) -> dict[str, Any]:
        state = self._state()
        sensors = self._sensor_payload(state)
        irrigation = state.get("irrigation") or {}
        network = state.get("network") or {}
        problems: list[dict[str, str]] = []
        for name, item in sensors.items():
            if not item.get("valid"):
                problems.append({"code": "SENSOR_INVALID", "sensor": name, "message": str(item.get("error") or "invalid")})
            elif item.get("stale"):
                problems.append({"code": "SENSOR_STALE", "sensor": name, "message": "age %ss" % item.get("age_s")})
        if not network.get("ip"):
            problems.append({"code": "NETWORK_OFFLINE", "sensor": "", "message": "no device IP"})
        if irrigation.get("state") == "fault":
            problems.append({"code": "IRRIGATION_FAULT", "sensor": "", "message": "pump is in fault state"})
        return {
            "ok": not problems,
            "problems": problems,
            "health": self.client.health(),
            "network": network,
            "irrigation": irrigation,
            "source": state.get("meta", {}).get("source"),
        }

    # ---------------------------------------------------------------- controls
    def _control_gate(self) -> None:
        if not self.allow_control:
            raise ServiceError(
                "CONTROL_DISABLED",
                "control tools are disabled; set AGRI_ALLOW_CONTROL=1 on the MCP server",
            )

    @staticmethod
    def _confirm(actual: str, expected: str, code: str) -> None:
        if actual != expected:
            raise ServiceError(code, "confirmation must be exactly %s" % expected)

    @staticmethod
    def _request_id(request_id: str | None) -> str:
        if request_id:
            return str(request_id)[:80]
        return "mcp-%d-%s" % (int(time.time()), uuid.uuid4().hex[:8])

    def start_irrigation(self, confirm: str, request_id: str | None = None) -> dict[str, Any]:
        self._control_gate()
        self._confirm(confirm, CONFIRM_START, "CONFIRM_REQUIRED")
        rid = self._request_id(request_id)
        AUDIT.info("control=start request_id=%s", rid)
        result = self.client.command("start", rid)
        return {
            "accepted": True,
            "request_id": rid,
            "irrigation": result.get("irrigation"),
            "note": "device max_run_s still applies",
        }

    def stop_irrigation(self, request_id: str | None = None) -> dict[str, Any]:
        # Stop is always available, even when control tools are disabled.
        rid = self._request_id(request_id)
        AUDIT.info("control=stop request_id=%s", rid)
        result = self.client.command("stop", rid)
        return {"accepted": True, "request_id": rid, "irrigation": result.get("irrigation")}

    def set_irrigation_mode(self, mode: str, confirm: str) -> dict[str, Any]:
        self._control_gate()
        self._confirm(confirm, CONFIRM_MODE, "CONFIRM_REQUIRED")
        if mode not in ("auto", "manual"):
            raise ServiceError("BAD_MODE", "mode must be auto or manual")
        AUDIT.info("control=set_mode mode=%s", mode)
        config = self.client.update_config({"irrigation": {"mode": mode}})
        return {"mode": mode, "config": redact(config)}

    def set_soil_threshold(self, percent: float, confirm: str) -> dict[str, Any]:
        self._control_gate()
        self._confirm(confirm, CONFIRM_THRESHOLD, "CONFIRM_REQUIRED")
        value = float(percent)
        if not (0 <= value <= 100):
            raise ServiceError("BAD_THRESHOLD", "threshold must be between 0 and 100")
        AUDIT.info("control=set_threshold value=%s", value)
        config = self.client.update_config({"irrigation": {"soil_threshold": value}})
        return {"soil_threshold": value, "config": redact(config)}

    def apply_plant_profile(self, profile: str, stage: str, confirm: str) -> dict[str, Any]:
        self._control_gate()
        self._confirm(confirm, CONFIRM_PROFILE, "CONFIRM_REQUIRED")
        if not profile or not stage:
            raise ServiceError("BAD_PROFILE", "profile and stage are required")
        AUDIT.info("control=apply_profile profile=%s stage=%s", profile, stage)
        config = self.client.update_config({"plant": {"profile": profile, "stage": stage}})
        return {"profile": profile, "stage": stage, "config": redact(config)}

    def import_plant_profiles(self, payload: dict[str, Any], confirm: str) -> dict[str, Any]:
        self._control_gate()
        self._confirm(confirm, CONFIRM_IMPORT, "CONFIRM_REQUIRED")
        if not isinstance(payload, dict):
            raise ServiceError("BAD_IMPORT", "payload must be a plant profile object")
        AUDIT.info("control=import_profiles")
        result = self.client.import_profiles(payload)
        return {"imported": result.get("imported", []), "profiles": result.get("profiles")}
