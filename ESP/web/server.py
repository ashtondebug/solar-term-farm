"""Minimal HTTP/1.1 server for MicroPython (and CPython tests).

Only the subset the dashboard needs is implemented: one request per
connection, GET/PUT/POST, JSON API routes and small static files.  Responses
always close the connection, which keeps the browser and the device simple.
"""

import json
import os

try:
    import asyncio
except ImportError:  # pragma: no cover - MicroPython < 1.20
    import uasyncio as asyncio

try:
    from urllib.parse import unquote
except ImportError:  # pragma: no cover - MicroPython without urllib.parse
    def unquote(value):
        return value.replace("%20", " ")

from version import VERSION

MAX_HEADER_BYTES = 8192
MAX_BODY_BYTES = 4096
REQUEST_TIMEOUT_S = 5
MAX_CLIENTS = 6

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


class HttpError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


class WebServer:
    def __init__(self, api, static_dir, host="0.0.0.0", port=80, logger=None):
        self.api = api
        self.static_dir = static_dir.rstrip("/")
        self.host = host
        self.port = port
        self.logger = logger
        self.server = None
        self._active = 0

    async def start(self):
        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
        if self.logger:
            self.logger.info("web server listening on %s:%s", self.host, self.port)
        return self.server

    async def serve_forever(self):
        await self.start()
        while True:
            await asyncio.sleep(3600)

    async def stop(self):
        if self.server is not None:
            self.server.close()
            try:
                await self.server.wait_closed()
            except Exception:
                pass
            self.server = None

    async def _handle_client(self, reader, writer):
        if self._active >= MAX_CLIENTS:
            try:
                writer.close()
            except Exception:
                pass
            return
        self._active += 1
        try:
            method, path, headers, raw_body = await self._read_request(reader)
            if method == "OPTIONS":
                await self._send(writer, 204, b"", "text/plain", {})
                return
            if path.startswith("/api/"):
                body = None
                if raw_body:
                    try:
                        body = json.loads(raw_body.decode("utf-8"))
                    except Exception:
                        await self._send_json(writer, 400, _error_body("BAD_JSON", "request body is not valid JSON"))
                        return
                result = self.api.handle(method, path, body, headers)
                await self._send_json(writer, result["status"], result["body"])
                return
            await asyncio.wait_for(self._send_static(writer, path), 10)
        except HttpError as exc:
            await self._send_json(writer, exc.status, _error_body("HTTP_%s" % exc.status, exc.message))
        except Exception as exc:
            if self.logger:
                self.logger.warn("connection failed: %s", exc)
            try:
                await self._send_json(writer, 500, _error_body("INTERNAL", "internal error"))
            except Exception:
                pass
        finally:
            self._active = max(0, self._active - 1)
            try:
                writer.close()
                await asyncio.wait_for(writer.wait_closed(), 1)
            except Exception:
                pass

    async def _read_request(self, reader):
        line = await asyncio.wait_for(reader.readline(), REQUEST_TIMEOUT_S)
        if not line:
            raise HttpError(400, "empty request")
        try:
            method, path, _version = parse_request_line(line)
        except ValueError:
            raise HttpError(400, "malformed request line")

        headers = {}
        total = 0
        while True:
            raw = await asyncio.wait_for(reader.readline(), REQUEST_TIMEOUT_S)
            if raw in (b"\r\n", b"\n", b""):
                break
            total += len(raw)
            if total > MAX_HEADER_BYTES:
                raise HttpError(431, "headers too large")
            key, _, value = raw.decode("utf-8").partition(":")
            if key:
                headers[key.strip().lower()] = value.strip()

        length = int(headers.get("content-length", "0") or 0)
        if length < 0 or length > MAX_BODY_BYTES:
            raise HttpError(413, "body too large")
        body = b""
        if length:
            body = await asyncio.wait_for(reader.readexactly(length), REQUEST_TIMEOUT_S)
        return method.upper(), unquote(path), headers, body

    async def _send_json(self, writer, status, payload):
        body = json.dumps(payload).encode("utf-8")
        await self._send(writer, status, body, "application/json; charset=utf-8", {"Cache-Control": "no-store"})

    async def _send_static(self, writer, path):
        if path == "/":
            path = "/index.html"
        if ".." in path or path.startswith("//"):
            raise HttpError(403, "forbidden path")
        file_path = self.static_dir + path
        try:
            stat = os.stat(file_path)
        except OSError:
            raise HttpError(404, "not found")
        size = stat[6]
        extension = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
        content_type = CONTENT_TYPES.get(extension, "application/octet-stream")
        header = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: %s\r\n"
            "Content-Length: %d\r\n"
            "Cache-Control: no-store\r\n"
            "X-Content-Type-Options: nosniff\r\n"
            "Connection: close\r\n\r\n"
        ) % (content_type, size)
        writer.write(header.encode("utf-8"))
        with open(file_path, "rb") as handle:
            while True:
                chunk = handle.read(2048)
                if not chunk:
                    break
                writer.write(chunk)
                await writer.drain()

    async def _send(self, writer, status, body, content_type, extra_headers):
        reason = {200: "OK", 204: "No Content", 400: "Bad Request", 401: "Unauthorized",
                  403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed",
                  409: "Conflict", 413: "Payload Too Large", 422: "Unprocessable Entity",
                  500: "Internal Server Error"}.get(status, "Error")
        header = "HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %d\r\nConnection: close\r\n" % (
            status, reason, content_type, len(body)
        )
        for key, value in (extra_headers or {}).items():
            header += "%s: %s\r\n" % (key, value)
        header += "\r\n"
        writer.write(header.encode("utf-8"))
        if body:
            writer.write(body)
        await writer.drain()


def parse_request_line(line):
    text = line.decode("utf-8").strip()
    parts = text.split(" ")
    if len(parts) != 3:
        raise ValueError("bad request line")
    return parts[0], parts[1], parts[2]


def _error_body(code, message):
    return {"ok": False, "error": {"code": code, "message": message}, "ts": 0}
