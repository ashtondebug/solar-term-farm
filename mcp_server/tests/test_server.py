"""FastMCP registration and protocol tests."""

from __future__ import annotations

import asyncio
import json
import unittest

from mcp.shared.memory import create_connected_server_and_client_session

from agriverse_mcp.server import build_server
from agriverse_mcp.service import AgriVerseService

try:
    from .fake_client import FakeClient
except ImportError:
    from fake_client import FakeClient


def _service(allow_control: bool) -> AgriVerseService:
    return AgriVerseService(FakeClient(), allow_control=allow_control)


class RegistrationTests(unittest.TestCase):
    def _tools(self, allow_control: bool) -> set[str]:
        server = build_server(_service(allow_control))
        tools = asyncio.run(server.list_tools())
        return {tool.name for tool in tools}

    def test_read_only_hides_control_but_keeps_stop(self):
        names = self._tools(False)
        self.assertIn("get_environment", names)
        self.assertIn("stop_irrigation", names)
        self.assertNotIn("start_irrigation", names)
        self.assertNotIn("set_soil_threshold", names)

    def test_control_mode_registers_start(self):
        names = self._tools(True)
        self.assertIn("start_irrigation", names)
        self.assertIn("set_soil_threshold", names)
        self.assertIn("apply_plant_profile", names)

    def test_import_tool_present_in_control_mode(self):
        self.assertIn("import_plant_profiles", self._tools(True))


class ProtocolTests(unittest.TestCase):
    def test_initialize_and_call_tool(self):
        async def run():
            server = build_server(_service(False))
            async with create_connected_server_and_client_session(server) as session:
                init = await session.initialize()
                self.assertEqual(init.serverInfo.name, "AgriVerse")
                result = await session.call_tool("get_environment", {})
                self.assertFalse(result.isError)
                payload = json.loads(result.content[0].text)
                self.assertIn("sensors", payload)
                self.assertEqual(payload["sensors"]["air_temp"]["value"], 24.5)

        asyncio.run(run())

    def test_control_tool_is_rejected_when_not_registered(self):
        async def run():
            server = build_server(_service(False))
            async with create_connected_server_and_client_session(server) as session:
                await session.initialize()
                result = await session.call_tool("start_irrigation", {"confirm": "START_IRRIGATION"})
                self.assertTrue(result.isError)

        asyncio.run(run())

    def test_control_tool_calls_device_when_enabled(self):
        async def run():
            client = FakeClient()
            server = build_server(AgriVerseService(client, allow_control=True))
            async with create_connected_server_and_client_session(server) as session:
                await session.initialize()
                result = await session.call_tool(
                    "start_irrigation",
                    {"confirm": "START_IRRIGATION", "request_id": "mcp-test-start"},
                )
                self.assertFalse(result.isError)
                data = json.loads(result.content[0].text)
                self.assertTrue(data["accepted"])
                self.assertEqual(client.commands, [("start", "mcp-test-start")])

        asyncio.run(run())

    def test_resources_and_prompts(self):
        async def run():
            server = build_server(_service(False))
            async with create_connected_server_and_client_session(server) as session:
                await session.initialize()
                resources = await session.list_resources()
                uris = {str(item.uri) for item in resources.resources}
                self.assertIn("agriverse://state", uris)
                prompts = await session.list_prompts()
                self.assertIn("daily_briefing", {item.name for item in prompts.prompts})

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
