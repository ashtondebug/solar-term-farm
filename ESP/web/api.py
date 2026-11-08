"""HTTP JSON API shared by the ESP32 server and the host simulator.

The API owns no hardware.  It reads the device state, delegates intents to the
irrigation controller, validates configuration and returns the envelope
``{"ok": true, "data": ...}`` / ``{"ok": false, "error": {...}}``.
"""

from config import ConfigError, deep_merge, public_config, validate_config
from core.timeutil import format_local
from solar_terms.astronomy import all_payloads, current_term
from suitability.plants import normalize_import, profile_names, stage_names
from version import VERSION


class ApiError(Exception):
    def __init__(self, status, code, message):
        self.status = status
        self.code = code
        self.message = message


class DeviceApi:
    def __init__(self, state, controller, config_store, history, config, clock, logger, source="device", plant_store=None):
        self.state = state
        self.controller = controller
        self.config_store = config_store
        self.history = history
        self.config = config
        self.clock = clock
        self.logger = logger
        self.source = source
        self.plant_store = plant_store
        self._term_cache = None
        self._term_cache_ts = 0

    # ------------------------------------------------------------------ HTTP
    def handle(self, method, path, body, headers):
        try:
            method = method.upper()
            path, query = _split_path(path)
            if method == "GET" and path == "/api/v1/state":
                return self._ok(self.get_state())
            if method == "GET" and path == "/api/v1/history":
                return self._ok(self.get_history(query))
            if method == "GET" and path == "/api/v1/solar-terms":
                return self._ok(self.get_solar_terms())
            if method == "GET" and path == "/api/v1/plant-profiles":
                return self._ok(self.get_plant_profiles())
            if method == "POST" and path == "/api/v1/plant-profiles/import":
                self._authorize(headers)
                return self._ok(self.import_plant_profiles(body or {}))
            if method == "GET" and path == "/api/v1/config":
                return self._ok(self.config_store.public())
            if method == "PUT" and path == "/api/v1/config":
                self._authorize(headers)
                return self._ok(self.update_config(body or {}))
            if method == "POST" and path == "/api/v1/irrigation/commands":
                self._authorize(headers)
                return self._ok(self.control(body or {}))
            if method == "POST" and path == "/api/v1/time":
                return self._ok(self.sync_time(body or {}))
            if method == "GET" and path == "/api/v1/health":
                return self._ok(self.health())
            raise ApiError(404, "NOT_FOUND", "unknown endpoint: %s" % path)
        except ApiError as exc:
            return self._error(exc.status, exc.code, exc.message)
        except Exception as exc:
            self.logger.error("api failure: %s", exc)
            return self._error(500, "INTERNAL", "internal error")

    # --------------------------------------------------------------- read ops
    def get_state(self):
        now = self.clock.now()
        offset = int(self.config.get("device", {}).get("timezone_offset", 28800))
        synced = bool(getattr(self.clock, "synced", False))
        data = self.state.snapshot(now)
        data["device"]["now"] = now
        data["device"]["time_synced"] = synced
        data["device"]["now_local"] = format_local(now, offset) if synced else ""
        data["device"]["source"] = self.source
        data["device"]["version"] = VERSION
        data["security"] = {"pin_required": bool(self.config.get("security", {}).get("require_pin"))}
        data["config"] = public_config(self.config)
        data["solar_term"] = self._term(now, synced)
        data["meta"] = {"source": self.source, "ts": now}
        return data

    def get_history(self, query):
        label = query.get("range", "12h")
        seconds = {"12h": 12 * 3600, "24h": 24 * 3600, "7d": 7 * 86400}.get(label)
        if seconds is None:
            raise ApiError(400, "BAD_RANGE", "range must be 12h, 24h or 7d")
        now = self.clock.now()
        return {"range": label, "points": self.history.range(seconds, now)}

    def get_solar_terms(self):
        now = self.clock.now()
        synced = bool(getattr(self.clock, "synced", False))
        if not synced:
            return {"current": None, "time_synced": False, "terms": all_payloads(now)}
        return {"current": current_term(now)["name"], "time_synced": True, "terms": all_payloads(now)}

    def get_plant_profiles(self):
        return {"profiles": profile_names(), "stages": stage_names()}

    def import_plant_profiles(self, payload):
        if self.plant_store is None:
            raise ApiError(500, "PLANT_STORE_MISSING", "plant profile store is not available")
        try:
            profiles = normalize_import(payload)
        except ValueError as exc:
            raise ApiError(422, "INVALID_PROFILES", str(exc))
        merged = {item["key"]: item for item in self.plant_store.profiles}
        for profile in profiles:
            merged[profile["key"]] = profile
        try:
            self.plant_store.save(list(merged.values()))
        except Exception as exc:
            raise ApiError(500, "PROFILE_SAVE_FAILED", "could not save plant profiles: %s" % exc)
        return {
            "profiles": profile_names(),
            "stages": stage_names(),
            "imported": [profile["key"] for profile in profiles],
        }

    def health(self):
        now = self.clock.now()
        return {"version": VERSION, "uptime_s": self.state.get("device.uptime_s", 0), "now": now}

    # -------------------------------------------------------------- write ops
    def update_config(self, payload):
        if not isinstance(payload, dict):
            raise ApiError(400, "BAD_BODY", "body must be a JSON object")
        allowed = {}
        for key in ("irrigation", "plant", "calibration"):
            if key in payload:
                if not isinstance(payload[key], dict):
                    raise ApiError(400, "BAD_BODY", "%s must be an object" % key)
                allowed[key] = payload[key]
        if not allowed:
            raise ApiError(400, "NOTHING_TO_UPDATE", "no supported config section supplied")

        merged = deep_merge(self.config, allowed)
        errors = validate_config(merged)
        if errors:
            raise ApiError(422, "INVALID_CONFIG", "; ".join(errors))
        # Mutate in place: the controller holds a reference to this dict.
        self.config.clear()
        self.config.update(merged)
        try:
            self.config_store.save(self.config)
        except ConfigError as exc:
            raise ApiError(422, "INVALID_CONFIG", str(exc))
        self.controller.publish(self.clock.now())
        return self.config_store.public()

    def control(self, payload):
        action = payload.get("action")
        request_id = payload.get("request_id")
        if action not in ("start", "stop"):
            raise ApiError(400, "BAD_ACTION", "action must be 'start' or 'stop'")
        if not request_id or not isinstance(request_id, str):
            raise ApiError(400, "MISSING_REQUEST_ID", "request_id is required")
        now = self.clock.now()
        result = self.controller.request(action, "manual", request_id, now)
        if not result.get("ok"):
            raise ApiError(409, result.get("code", "CONTROL_FAILED"), result.get("message", "control failed"))
        return {"irrigation": self.state.get("irrigation"), "request_id": request_id}

    def sync_time(self, payload):
        epoch = payload.get("epoch")
        if not isinstance(epoch, (int, float)) or isinstance(epoch, bool):
            raise ApiError(400, "BAD_EPOCH", "epoch must be a number")
        epoch = int(epoch)
        if epoch < 1577836800 or epoch > 4102444800:
            raise ApiError(400, "BAD_EPOCH", "epoch is outside the supported range")
        self.clock.set_epoch(epoch)
        self.state.set_device(time_synced=True, now=epoch)
        return {"now": epoch, "time_synced": True}

    # ----------------------------------------------------------------- helpers
    def _authorize(self, headers):
        security = self.config.get("security", {})
        if not security.get("require_pin"):
            return
        supplied = (headers or {}).get("x-agriverse-pin", "")
        expected = security.get("pin", "")
        if not supplied:
            raise ApiError(401, "PIN_REQUIRED", "device PIN required")
        if not _safe_equal(supplied, expected):
            raise ApiError(401, "PIN_INVALID", "device PIN is incorrect")

    def _term(self, now, synced):
        if not synced:
            return {
                "name": "—",
                "index": -1,
                "season": "",
                "angle": 0,
                "date_hint": "",
                "intro": "设备时间尚未同步，无法计算当前节气。",
                "proverbs": [],
                "customs": [],
                "tips": [],
                "available": False,
                "start_ts": None,
                "end_ts": None,
                "time_synced": False,
            }
        if self._term_cache is not None and (now - self._term_cache_ts) < 3600:
            return self._term_cache
        try:
            self._term_cache = current_term(now)
            self._term_cache_ts = now
        except Exception as exc:
            self.logger.warn("solar term failed: %s", exc)
            self._term_cache = None
        return self._term_cache

    def _ok(self, data):
        return {"status": 200, "body": {"ok": True, "data": data, "ts": self.clock.now()}}

    def _error(self, status, code, message):
        return {
            "status": status,
            "body": {"ok": False, "error": {"code": code, "message": message}, "ts": self.clock.now()},
        }


def _split_path(path):
    if "?" not in path:
        return path, {}
    route, raw = path.split("?", 1)
    query = {}
    for part in raw.split("&"):
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
            query[key] = value
    return route, query


def _safe_equal(left, right):
    if len(left) != len(right):
        return False
    diff = 0
    for a, b in zip(left, right):
        diff |= ord(a) ^ ord(b)
    return diff == 0
