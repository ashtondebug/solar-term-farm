"""Host tests for the button intent logic (no hardware)."""

from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401
from button import PumpButton


class FakePin:
    def __init__(self):
        self.value_ = 0

    def value(self):
        return self.value_


class FakeRelay:
    def __init__(self):
        self.on = False


class FakeController:
    def __init__(self):
        self.relay = FakeRelay()
        self.requests = []
        self.last_stop_ts = None
        self.irrigation_config = {"min_off_s": 5}

    def request(self, action, trigger, request_id, now):
        self.requests.append((action, trigger, request_id, now))
        self.relay.on = action == "start"
        return {"ok": True}


class FakeLogger:
    def info(self, *_args):
        pass

    def warn(self, *_args):
        pass


class FakeClock:
    def now(self):
        return 1234


class ButtonTests(unittest.TestCase):
    def test_rising_press_starts_one_request(self):
        controller = FakeController()
        button = PumpButton(FakePin(), controller, FakeClock(), FakeLogger())
        button.pin.value_ = 1
        self.assertTrue(button.trigger())
        self.assertEqual(controller.requests, [("start", "button", "button-1234-1", 1234)])
        self.assertTrue(controller.relay.on)

    def test_button_toggles_start_and_stop(self):
        controller = FakeController()
        button = PumpButton(FakePin(), controller, FakeClock(), FakeLogger())
        button.pin.value_ = 1
        self.assertTrue(button.trigger())
        self.assertTrue(controller.relay.on)
        self.assertTrue(button.trigger())
        self.assertFalse(controller.relay.on)
        self.assertEqual([item[0] for item in controller.requests], ["start", "stop"])


if __name__ == "__main__":
    unittest.main()
