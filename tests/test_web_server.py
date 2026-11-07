import asyncio
import tempfile
import unittest
from pathlib import Path

import _bootstrap  # noqa: F401
from web.server import WebServer


class FakeApi:
    def handle(self, method, path, body, headers):
        return {"status": 200, "body": {"ok": True, "path": path, "method": method}}


class WebServerTests(unittest.TestCase):
    def test_api_roundtrip(self):
        root = Path(tempfile.mkdtemp(prefix="agri-web-"))
        (root / "index.html").write_text("<html>ok</html>", encoding="utf-8")

        async def run():
            server = WebServer(FakeApi(), str(root), "127.0.0.1", 0)
            await server.start()
            port = server.server.sockets[0].getsockname()[1]
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(b"GET /api/v1/health HTTP/1.1\r\nHost: test\r\n\r\n")
            await writer.drain()
            data = await reader.read()
            writer.close()
            await server.stop()
            return data

        data = asyncio.run(run())
        self.assertIn(b"HTTP/1.1 200 OK", data)
        self.assertIn(b'"ok": true', data)
        self.assertIn(b"/api/v1/health", data)

    def test_static_index(self):
        root = Path(tempfile.mkdtemp(prefix="agri-web-"))
        (root / "index.html").write_text("<html>hello</html>", encoding="utf-8")

        async def run():
            server = WebServer(FakeApi(), str(root), "127.0.0.1", 0)
            await server.start()
            port = server.server.sockets[0].getsockname()[1]
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(b"GET / HTTP/1.1\r\nHost: test\r\n\r\n")
            await writer.drain()
            data = await reader.read()
            writer.close()
            await server.stop()
            return data

        data = asyncio.run(run())
        self.assertIn(b"HTTP/1.1 200 OK", data)
        self.assertIn(b"<html>hello</html>", data)


if __name__ == "__main__":
    unittest.main()
