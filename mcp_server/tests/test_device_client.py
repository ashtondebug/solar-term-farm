"""Tests for the REST client wrapper and error mapping."""

from __future__ import annotations

import json
import unittest

import httpx

from agriverse_mcp.device_client import DeviceClient, DeviceError


def _client(handler) -> DeviceClient:
    return DeviceClient(
        "http://device.test",
        pin="123456",
        timeout_s=2,
        transport=httpx.MockTransport(handler),
    )


class DeviceClientTests(unittest.TestCase):
    def test_get_state_unwraps_envelope(self):
        def handler(request):
            self.assertEqual(request.url.path, "/api/v1/state")
            return httpx.Response(200, json={"ok": True, "data": {"pump": False}})

        self.assertEqual(_client(handler).state(), {"pump": False})

    def test_control_sends_pin_and_request_id(self):
        def handler(request):
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.headers["x-agriverse-pin"], "123456")
            body = json.loads(request.content)
            self.assertEqual(body, {"action": "start", "request_id": "abc"})
            return httpx.Response(200, json={"ok": True, "data": {"request_id": "abc"}})

        result = _client(handler).command("start", "abc")
        self.assertEqual(result["request_id"], "abc")

    def test_control_error_preserves_code(self):
        def handler(_request):
            return httpx.Response(
                409,
                json={"ok": False, "error": {"code": "ALREADY_RUNNING", "message": "pump is already running"}},
            )

        with self.assertRaises(DeviceError) as ctx:
            _client(handler).command("start", "abc")
        self.assertEqual(ctx.exception.code, "ALREADY_RUNNING")
        self.assertEqual(ctx.exception.status, 409)

    def test_network_error_is_stable(self):
        def handler(_request):
            raise httpx.ConnectError("offline")

        with self.assertRaises(DeviceError) as ctx:
            _client(handler).state()
        self.assertEqual(ctx.exception.code, "DEVICE_UNREACHABLE")


if __name__ == "__main__":
    unittest.main()
