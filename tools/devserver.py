#!/usr/bin/env python3
"""Host-side simulator for the M1 vertical slice.

It runs the *real* API/controller/state code against fake hardware, serves the
same static assets the ESP32 will serve, and labels every response with
``X-AgriVerse-Source: simulator``.  The browser shows a persistent banner, so
simulated values are never mistaken for a real device.
"""

import argparse
import json
import logging
import math
import sys
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ESP"))

from config import default_config, public_config  # noqa: E402
from core.state import DeviceState  # noqa: E402
from core.timeutil import format_local  # noqa: E402
from irrigation.controller import IrrigationController  # noqa: E402
from irrigation.history import IrrigationHistory  # noqa: E402
from irrigation.relay import Relay  # noqa: E402
from sensors.base import Reading  # noqa: E402
from solar_terms.astronomy import current_term  # noqa: E402
from storage.history_store import HistoryStore  # noqa: E402
from suitability.model import evaluate  # noqa: E402
from suitability.plants import get_profile  # noqa: E402
from version import VERSION  # noqa: E402
from web.api import DeviceApi  # noqa: E402

LOG = logging.getLogger("agriverse.sim")
STATIC = ROOT / "ESP" / "web" / "static"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


class FakePin:
    def __init__(self):
        self._value = 0
        self.writes = []

    def value(self, new_value=None):
        if new_value is None:
            return self._value
        self._value = int(new_value)
        self.writes.append(self._value)


class SimClock:
    synced = True

    def now(self):
        return int(time.time())

    def set_epoch(self, epoch):
        # The simulator follows the host clock; accept the call for API parity.
        return True


class MemoryConfigStore:
    def __init__(self, config):
        self.config = config

    def get(self):
        return self.config

    def public(self):
        return public_config(self.config)

    def save(self, config):
        self.config = config


class SimBackend:
    def __init__(self):
        self.lock = threading.Lock()
        self.config = default_config()
        self.config["security"]["require_pin"] = False
        self.clock = SimClock()
        self.state = DeviceState(source="simulator", version=VERSION)
        self.now = self.clock.now()
        self.state.mark_boot(self.now)
        self.relay = Relay(FakePin(), active_high=True)
        self.history = HistoryStore(tempfile.mkdtemp(prefix="agriverse-sim-"))
        self.controller = IrrigationController(
            self.relay,
            self.config,
            self.clock,
            self.state,
            IrrigationHistory(),
            LOG,
        )
        self.config_store = MemoryConfigStore(self.config)
        self.api = DeviceApi(
            self.state,
            self.controller,
            self.config_store,
            self.history,
            self.config,
            self.clock,
            LOG,
            source="simulator",
        )
        self._seed_history()

    def _seed_history(self):
        points = []
        now = self.now
        for index in range(288, 0, -1):
            ts = now - index * 300
            soil = 42.0 + 6.0 * math.sin(ts / 5400.0)
            temp = 24.6 + 2.0 * math.sin(ts / 10800.0)
            humidity = 63.0 + 5.0 * math.sin(ts / 7200.0)
            light = max(0.0, 12680.0 + 5000.0 * math.sin(ts / 3600.0))
            points.append(
                {
                    "ts": ts,
                    "temp": round(temp, 2),
                    "humidity": round(humidity, 2),
                    "soil": round(soil, 2),
                    "light": round(light, 0),
                    "suitability": 80,
                }
            )
        self.history.seed(points)
        self._last_history = now

    def update(self):
        now = self.clock.now()
        soil = 42.0 + 6.0 * math.sin(now / 5400.0)
        temp = 24.6 + 2.0 * math.sin(now / 10800.0)
        humidity = 63.0 + 5.0 * math.sin(now / 7200.0)
        light = max(0.0, 12680.0 + 5000.0 * math.sin(now / 3600.0))
        readings = {
            "soil": Reading(soil, "%", True, now),
            "air_temp": Reading(temp, "C", True, now),
            "air_humidity": Reading(humidity, "%", True, now),
            "light": Reading(light, "lx", True, now),
        }
        for name, reading in readings.items():
            self.state.set_sensor(name, reading, now)
        result = evaluate(readings, get_profile(self.config["plant"]["profile"]), now, 90)
        self.state.set_suitability(result, now)
        self.state.set_network(
            {
                "wifi": "connected",
                "status": "connected",
                "ssid": "AgriVerse-Sim",
                "ip": "127.0.0.1",
                "rssi": -42,
                "attempts": 0,
                "last_error": None,
            }
        )
        self.state.set_device(
            time_synced=True,
            now=now,
            now_local=format_local(now, self.config["device"]["timezone_offset"]),
            source="simulator",
        )
        self.state.set_uptime(now - self.state.boot_ts)
        self.controller.tick(now, readings["soil"])
        interval = int(self.config["sampling"]["history_interval_s"])
        if now - self._last_history >= interval:
            self.history.append(
                {
                    "ts": now,
                    "temp": round(temp, 2),
                    "humidity": round(humidity, 2),
                    "soil": round(soil, 2),
                    "light": round(light, 0),
                    "suitability": result.get("score"),
                },
                now,
            )
            self._last_history = now


class Handler(BaseHTTPRequestHandler):
    server_version = "AgriVerseSim/0.1"

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_OPTIONS(self):
        self._respond(204, b"", "text/plain")

    def _dispatch(self, method):
        backend = self.server.backend
        parsed = urlparse(self.path)
        try:
            if parsed.path.startswith("/api/"):
                length = int(self.headers.get("Content-Length", "0") or 0)
                body = None
                if length:
                    raw = self.rfile.read(length)
                    body = json.loads(raw.decode("utf-8"))
                headers = {key.lower(): value for key, value in self.headers.items()}
                with backend.lock:
                    backend.update()
                    result = backend.api.handle(method, self.path, body, headers)
                payload = json.dumps(result["body"], ensure_ascii=False).encode("utf-8")
                self._respond(result["status"], payload, "application/json; charset=utf-8")
                return
            self._serve_static(parsed.path)
        except Exception as exc:
            LOG.exception("request failed: %s", exc)
            payload = json.dumps(
                {"ok": False, "error": {"code": "SIM_ERROR", "message": str(exc)}}, ensure_ascii=False
            ).encode("utf-8")
            self._respond(500, payload, "application/json; charset=utf-8")

    def _serve_static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        if ".." in path:
            self._respond(403, b"forbidden", "text/plain")
            return
        target = (STATIC / path.lstrip("/")).resolve()
        if not str(target).startswith(str(STATIC.resolve())) or not target.is_file():
            self._respond(404, b"not found", "text/plain")
            return
        body = target.read_bytes()
        self._respond(200, body, CONTENT_TYPES.get(target.suffix.lower(), "application/octet-stream"))

    def _respond(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-AgriVerse-Source", "simulator")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        LOG.debug("%s - %s", self.address_string(), fmt % args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--open", action="store_true", help="open the dashboard in a browser")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not (STATIC / "index.html").is_file():
        LOG.info("building web assets")
        sys.path.insert(0, str(ROOT / "tools"))
        import build_web

        if build_web.main() != 0:
            return 1

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True
    server.backend = SimBackend()
    url = "http://%s:%d/" % (args.host, args.port)
    print("AgriVerse M1 simulator")
    print("  url:  %s" % url)
    print("  data: SIMULATOR (not a real device)")
    print("  stop: Ctrl+C")
    if args.open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
