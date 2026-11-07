"""Single source of truth for the running device.

Every client (web, TJC screen, future MCP bridge or PC tools) reads from this
snapshot and submits *intents* to the irrigation controller.  No client writes
hardware directly.

Uptime is tracked separately from wall-clock time: the board may boot before
the browser syncs the clock, so subtracting the boot wall time from a later
synced time would produce a nonsensical uptime.
"""


class DeviceState:
    def __init__(self, source="device", version="0.1.0"):
        self.source = source
        self.version = version
        self.boot_ts = None
        self.uptime_s = 0
        self.data = {
            "device": {
                "name": "AgriVerse",
                "version": version,
                "model": "ESP32-S3 N16R8",
                "firmware": "MicroPython",
                "uptime_s": 0,
                "time_synced": False,
                "now": 0,
                "now_local": "",
                "source": source,
            },
            "sensors": {},
            "suitability": {
                "score": None,
                "status": "unavailable",
                "components": {},
                "reasons": ["waiting for first sample"],
                "ts": 0,
            },
            "solar_term": None,
            "irrigation": {
                "mode": "auto",
                "pump": False,
                "state": "idle",
                "remaining_s": 0,
                "last_start_ts": None,
                "last_stop_ts": None,
                "max_run_s": 20,
                "threshold": 35.0,
                "history": [],
            },
            "network": {
                "wifi": "offline",
                "status": "offline",
                "ip": "",
                "ssid": "",
                "rssi": None,
            },
            "security": {"pin_required": False},
            "meta": {"source": source, "ts": 0},
        }

    def set(self, path, value):
        parts = path.split(".")
        node = self.data
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value

    def get(self, path, default=None):
        node = self.data
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set_sensor(self, name, reading, now):
        payload = reading.as_dict()
        if not payload.get("valid"):
            payload["status"] = "uncalibrated" if payload.get("error") == "uncalibrated" else "error"
        else:
            payload["status"] = "ok"
        payload["ts"] = payload.get("ts") or now
        self.data["sensors"][name] = payload

    def set_suitability(self, result, now):
        result = dict(result or {})
        result.setdefault("ts", now)
        self.data["suitability"] = result

    def set_solar_term(self, term):
        self.data["solar_term"] = term

    def set_irrigation(self, status):
        self.data["irrigation"] = status

    def set_network(self, network):
        self.data["network"] = network

    def set_device(self, **fields):
        self.data["device"].update(fields)

    def set_uptime(self, seconds):
        self.uptime_s = max(0, int(seconds))
        self.data["device"]["uptime_s"] = self.uptime_s

    def set_meta(self, now):
        self.data["meta"]["ts"] = int(now)

    def mark_boot(self, now):
        self.boot_ts = int(now)
        self.uptime_s = 0

    def snapshot(self, now=None):
        if now is not None:
            self.data["meta"]["ts"] = int(now)
        self.data["device"]["uptime_s"] = self.uptime_s
        return self.data
