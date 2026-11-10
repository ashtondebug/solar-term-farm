"""Optional real-device MCP smoke test.

This script intentionally does not start the pump.  It reads the environment,
prints the irrigation status, and sends a stop command (safe when already
stopped).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main() -> int:
    env = dict(os.environ)
    env.setdefault("PYTHONPATH", str(ROOT))
    env.setdefault("AGRI_BASE_URL", "http://192.168.153.234")
    env.setdefault("AGRI_ALLOW_CONTROL", "1")
    env.setdefault("AGRI_TIMEOUT_S", "8")

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "agriverse_mcp"],
        cwd=str(ROOT),
        env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("server:", init.serverInfo.name)
            tools = await session.list_tools()
            print("tools:", len(tools.tools))
            result = await session.call_tool("get_environment", {})
            data = json.loads(result.content[0].text)
            for name, item in data["sensors"].items():
                print("%s: %s %s valid=%s stale=%s" % (
                    name, item.get("value"), item.get("unit"), item.get("valid"), item.get("stale")
                ))
            status = await session.call_tool("get_irrigation_status", {})
            print("irrigation:", status.content[0].text[:240])
            stop = await session.call_tool("stop_irrigation", {"request_id": "mcp-smoke-stop"})
            print("stop error:", stop.isError)
            print("stop:", stop.content[0].text[:240])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
