import unittest

import _bootstrap  # noqa: F401
from config import default_config, public_config
from core.state import DeviceState
from fakes.hardware import FakeClock
from web.api import DeviceApi, _safe_equal, _split_path


class MemoryStore:
    def __init__(self, config):
        self.config = config

    def public(self):
        return public_config(self.config)

    def save(self, config):
        self.config = config


class FakeHistory:
    def range(self, seconds, now):
        return [{"ts": now - 10, "temp": 24.0, "soil": 42.0}]


class FakeController:
    def __init__(self):
        self.calls = []

    def request(self, action, source, request_id, now):
        self.calls.append((action, source, request_id, now))
        return {"ok": True}

    def publish(self, now):
        pass


def make_api(require_pin=True, pin="123456"):
    config = default_config()
    config["security"]["require_pin"] = require_pin
    config["security"]["pin"] = pin
    state = DeviceState()
    controller = FakeController()
    store = MemoryStore(config)
    clock = FakeClock(1700000000)
    return DeviceApi(state, controller, store, FakeHistory(), config, clock, _Silent(), source="test"), config, controller, clock


class _Silent:
    def error(self, *args):
        pass

    def warn(self, *args):
        pass


class ApiTests(unittest.TestCase):
    def test_state_envelope(self):
        api, config, controller, clock = make_api()
        result = api.handle("GET", "/api/v1/state", None, {})
        self.assertEqual(result["status"], 200)
        body = result["body"]
        self.assertTrue(body["ok"])
        self.assertTrue(body["data"]["device"]["time_synced"])
        self.assertTrue(body["data"]["security"]["pin_required"])
        self.assertNotIn("pin", body["data"]["config"]["security"])

        clock.synced = False
        unsynced = api.handle("GET", "/api/v1/state", None, {})
        self.assertFalse(unsynced["body"]["data"]["device"]["time_synced"])
        self.assertEqual(unsynced["body"]["data"]["solar_term"]["name"], "—")

    def test_control_requires_pin(self):
        api, config, controller, clock = make_api()
        missing = api.handle("POST", "/api/v1/irrigation/commands", {"action": "start", "request_id": "r1"}, {})
        self.assertEqual(missing["status"], 401)
        wrong = api.handle(
            "POST",
            "/api/v1/irrigation/commands",
            {"action": "start", "request_id": "r1"},
            {"x-agriverse-pin": "000000"},
        )
        self.assertEqual(wrong["status"], 401)
        ok = api.handle(
            "POST",
            "/api/v1/irrigation/commands",
            {"action": "start", "request_id": "r1"},
            {"x-agriverse-pin": "123456"},
        )
        self.assertEqual(ok["status"], 200)
        self.assertEqual(controller.calls[0][0], "start")

    def test_config_validation(self):
        api, config, controller, clock = make_api(require_pin=False)
        bad = api.handle("PUT", "/api/v1/config", {"irrigation": {"max_run_s": 999}}, {})
        self.assertEqual(bad["status"], 422)
        good = api.handle("PUT", "/api/v1/config", {"irrigation": {"max_run_s": 30}}, {})
        self.assertEqual(good["status"], 200)
        self.assertEqual(config["irrigation"]["max_run_s"], 30)

    def test_time_sync(self):
        api, config, controller, clock = make_api(require_pin=False)
        result = api.handle("POST", "/api/v1/time", {"epoch": 1762500000}, {})
        self.assertEqual(result["status"], 200)
        self.assertEqual(clock.now(), 1762500000)

    def test_bad_range_and_unknown_route(self):
        api, config, controller, clock = make_api(require_pin=False)
        self.assertEqual(api.handle("GET", "/api/v1/history?range=bad", None, {})["status"], 400)
        self.assertEqual(api.handle("GET", "/api/v1/nope", None, {})["status"], 404)

    def test_helpers(self):
        self.assertEqual(_split_path("/a?x=1")[1]["x"], "1")
        self.assertTrue(_safe_equal("123456", "123456"))
        self.assertFalse(_safe_equal("123456", "123457"))


if __name__ == "__main__":
    unittest.main()
