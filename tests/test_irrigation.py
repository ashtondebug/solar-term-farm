import unittest

import _bootstrap  # noqa: F401
from config import default_config
from core.log import Logger
from core.state import DeviceState
from fakes.hardware import FakeClock, FakePin
from irrigation.controller import IrrigationController
from irrigation.history import IrrigationHistory
from irrigation.relay import Relay
from sensors.base import Reading


def build(mode="manual", max_run=10, min_off=5, min_interval=0):
    config = default_config()
    config["irrigation"].update(
        {
            "mode": mode,
            "max_run_s": max_run,
            "min_off_s": min_off,
            "min_interval_s": min_interval,
            "soil_threshold": 40.0,
            "hysteresis": 2.0,
            "sensor_stale_s": 90,
        }
    )
    pin = FakePin()
    relay = Relay(pin, active_high=True)
    state = DeviceState()
    clock = FakeClock(1000)
    history = IrrigationHistory()
    controller = IrrigationController(relay, config, clock, state, history, Logger("test", "error"))
    return config, pin, relay, state, clock, history, controller


class RelayTests(unittest.TestCase):
    def test_active_high_polarity(self):
        pin = FakePin()
        relay = Relay(pin, active_high=True)
        self.assertEqual(pin.value(), 0)
        relay.set(True, "test")
        self.assertEqual(pin.value(), 1)
        relay.off("test")
        self.assertEqual(pin.value(), 0)


class IrrigationTests(unittest.TestCase):
    def test_manual_start_and_max_run(self):
        config, pin, relay, state, clock, history, controller = build()
        result = controller.request("start", "manual", "r1", 1000)
        self.assertTrue(result["ok"])
        self.assertEqual(pin.value(), 1)
        self.assertTrue(state.get("irrigation.pump"))
        controller.tick(1010, None)
        self.assertEqual(pin.value(), 0)
        self.assertFalse(state.get("irrigation.pump"))
        self.assertEqual(history.recent(1)[0]["stop_reason"], "max_run")

    def test_min_off_blocks_restart(self):
        config, pin, relay, state, clock, history, controller = build()
        controller.request("start", "manual", "r1", 1000)
        controller.tick(1010, None)
        blocked = controller.request("start", "manual", "r2", 1012)
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "MIN_OFF")
        allowed = controller.request("start", "manual", "r3", 1016)
        self.assertTrue(allowed["ok"])

    def test_auto_starts_on_dry_soil(self):
        config, pin, relay, state, clock, history, controller = build(mode="auto")
        controller.tick(1000, Reading(30.0, "%", True, 1000))
        self.assertEqual(pin.value(), 1)
        self.assertEqual(state.get("irrigation.mode"), "auto")

    def test_auto_does_not_start_on_stale_soil(self):
        config, pin, relay, state, clock, history, controller = build(mode="auto")
        controller.tick(1000, Reading(30.0, "%", True, 800))
        self.assertEqual(pin.value(), 0)

    def test_auto_does_not_start_when_wet(self):
        config, pin, relay, state, clock, history, controller = build(mode="auto")
        controller.tick(1000, Reading(50.0, "%", True, 1000))
        self.assertEqual(pin.value(), 0)

    def test_request_id_is_idempotent(self):
        config, pin, relay, state, clock, history, controller = build()
        pin.writes.clear()
        first = controller.request("start", "manual", "same", 1000)
        second = controller.request("start", "manual", "same", 1000)
        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(len(pin.writes), 1)

    def test_fault_blocks_start(self):
        config, pin, relay, state, clock, history, controller = build()
        relay.fault = "test fault"
        result = controller.request("start", "manual", "r1", 1000)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "FAULT")

    def test_button_start_is_manual_state(self):
        config, pin, relay, state, clock, history, controller = build()
        result = controller.request("start", "button", "b1", 1000)
        self.assertTrue(result["ok"])
        self.assertEqual(state.get("irrigation.state"), "manual")

    def test_long_run_stops_at_max_run(self):
        config, pin, relay, state, clock, history, controller = build(max_run=10)
        controller.request("start", "auto", "long", 1000)
        # Simulate two hours of ticks; max_run must still win.
        for now in range(1001, 8201):
            controller.tick(now, None)
        self.assertEqual(pin.value(), 0)
        self.assertFalse(state.get("irrigation.pump"))
        record = history.recent(1)[0]
        self.assertEqual(record["stop_reason"], "max_run")
        self.assertEqual(record["duration_s"], 10)

    def test_fault_while_running_forces_pump_off_and_alarms(self):
        config, pin, relay, state, clock, history, controller = build()
        controller.request("start", "manual", "f1", 1000)
        self.assertEqual(pin.value(), 1)
        relay.fault = "injected relay fault"
        controller.tick(1001, None)
        self.assertEqual(pin.value(), 0)
        self.assertEqual(state.get("irrigation.state"), "fault")
        self.assertEqual(state.get("irrigation.alarm"), "FAULT")

    def test_clear_fault_drives_off_and_returns_idle(self):
        config, pin, relay, state, clock, history, controller = build()
        controller.request("start", "manual", "f1", 1000)
        relay.fault = "injected"
        controller.tick(1001, None)
        controller.clear_fault()
        self.assertEqual(pin.value(), 0)
        self.assertEqual(state.get("irrigation.state"), "idle")
        self.assertIsNone(state.get("irrigation.alarm"))


if __name__ == "__main__":
    unittest.main()
