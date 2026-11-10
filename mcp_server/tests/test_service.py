"""Tests for the MCP service layer; no network or hardware required."""

from __future__ import annotations

import unittest

from agriverse_mcp.service import (
    CONFIRM_IMPORT,
    CONFIRM_MODE,
    CONFIRM_PROFILE,
    CONFIRM_START,
    CONFIRM_THRESHOLD,
    AgriVerseService,
    ServiceError,
    redact,
)

try:
    from .fake_client import FakeClient
except ImportError:  # unittest discovery from the package root
    from fake_client import FakeClient


class ServiceReadTests(unittest.TestCase):
    def setUp(self):
        self.service = AgriVerseService(FakeClient(), allow_control=False)

    def test_environment_has_age_and_stale(self):
        data = self.service.get_environment()
        self.assertEqual(data["source"], "device")
        self.assertEqual(data["sensors"]["air_temp"]["age_s"], 5)
        self.assertFalse(data["sensors"]["air_temp"]["stale"])
        self.assertTrue(data["sensors"]["light"]["stale"])

    def test_sensor_status_not_all_ok(self):
        data = self.service.get_sensor_status()
        self.assertFalse(data["all_ok"])

    def test_config_redacts_secrets(self):
        config = self.service.get_config()
        self.assertEqual(config["security"]["pin"], "***")
        self.assertEqual(config["wifi"]["password"], "***")

    def test_history_range_validation(self):
        with self.assertRaises(ServiceError) as ctx:
            self.service.get_history("1h")
        self.assertEqual(ctx.exception.code, "BAD_RANGE")
        self.assertEqual(self.service.get_history("12h")["range"], "12h")

    def test_diagnose_reports_invalid_sensor(self):
        data = self.service.diagnose()
        self.assertFalse(data["ok"])
        self.assertTrue(any(item["code"] == "SENSOR_INVALID" for item in data["problems"]))


class ServiceControlTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.service = AgriVerseService(self.client, allow_control=True)

    def test_start_requires_exact_confirmation(self):
        with self.assertRaises(ServiceError) as ctx:
            self.service.start_irrigation("yes")
        self.assertEqual(ctx.exception.code, "CONFIRM_REQUIRED")
        self.assertEqual(self.client.commands, [])

    def test_start_uses_device_command(self):
        result = self.service.start_irrigation(CONFIRM_START, "test-1")
        self.assertTrue(result["accepted"])
        self.assertEqual(self.client.commands, [("start", "test-1")])

    def test_stop_always_available_even_read_only(self):
        read_only = AgriVerseService(self.client, allow_control=False)
        result = read_only.stop_irrigation("stop-1")
        self.assertTrue(result["accepted"])
        self.assertEqual(self.client.commands[-1], ("stop", "stop-1"))

    def test_start_blocked_when_control_disabled(self):
        read_only = AgriVerseService(self.client, allow_control=False)
        with self.assertRaises(ServiceError) as ctx:
            read_only.start_irrigation(CONFIRM_START)
        self.assertEqual(ctx.exception.code, "CONTROL_DISABLED")

    def test_mode_and_threshold(self):
        self.service.set_irrigation_mode("manual", CONFIRM_MODE)
        self.assertEqual(self.client.configs[-1], {"irrigation": {"mode": "manual"}})
        self.service.set_soil_threshold(42.5, CONFIRM_THRESHOLD)
        self.assertEqual(self.client.configs[-1], {"irrigation": {"soil_threshold": 42.5}})

    def test_profile_and_import(self):
        self.service.apply_plant_profile("tomato", "flowering", CONFIRM_PROFILE)
        self.assertEqual(
            self.client.configs[-1],
            {"plant": {"profile": "tomato", "stage": "flowering"}},
        )
        self.service.import_plant_profiles({"version": 1, "plants": []}, CONFIRM_IMPORT)
        self.assertEqual(len(self.client.imports), 1)

    def test_redact_nested_and_list(self):
        data = {"a": [{"pin": "1", "name": "x"}], "token": "t"}
        self.assertEqual(redact(data), {"a": [{"pin": "***", "name": "x"}], "token": "***"})


if __name__ == "__main__":
    unittest.main()
