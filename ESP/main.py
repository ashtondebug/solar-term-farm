"""AgriVerse firmware entry point.

Boot order is safety-first: the relay pin is driven LOW, then storage and
services are built, then the async loops start.  Hardware imports live only in
this file so every other module stays testable on CPython.
"""

import gc
import sys
import time

import machine
import network

try:
    import asyncio
except ImportError:  # pragma: no cover
    import uasyncio as asyncio

from core.log import Logger
from core.state import DeviceState
from core.timeutil import SystemClock, format_local
from irrigation.controller import IrrigationController
from irrigation.history import IrrigationHistory
from irrigation.relay import Relay
from network.manager import NetworkManager
from sensors.bh1750 import BH1750
from sensors.manager import SensorManager
from sensors.sht31 import SHT31
from sensors.soil import SoilSensor
from storage.config_store import ConfigStore
from storage.history_store import HistoryStore
from storage.kvstore import KVStore
from suitability.model import evaluate
from suitability.plants import get_profile
from version import DEVICE_MODEL, FIRMWARE, VERSION
from web.api import DeviceApi
from web.server import WebServer


class Application:
    def __init__(self):
        self.logger = Logger("agri", "info")
        self.config = None
        self.config_store = None
        self.state = None
        self.clock = None
        self.relay = None
        self.controller = None
        self.manager = None
        self.history = None
        self.network = None
        self.api = None
        self.web = None
        self.wdt = None

    def build(self):
        self.logger.info("booting AgriVerse %s", VERSION)
        self.boot_ticks = time.ticks_ms()
        self.wdt = machine.WDT(timeout=8000)

        # Safety first: drive the relay low before creating anything else.
        relay_pin = machine.Pin(5, machine.Pin.OUT, value=0)
        self.relay = Relay(relay_pin, active_high=True, logger=self.logger)

        rtc = machine.RTC()
        self.clock = SystemClock(rtc)
        self.state = DeviceState(source="device", version=VERSION)
        self.state.mark_boot(self.clock.now())

        kv = KVStore("/data", self.logger)
        self.config_store = ConfigStore(kv, self.logger)
        self.config = self.config_store.load()
        relay_number = int(self.config["pins"].get("relay", 5))
        if relay_number != 5:
            reviewed_pin = machine.Pin(relay_number, machine.Pin.OUT, value=0)
            self.relay = Relay(reviewed_pin, active_high=True, logger=self.logger)
            self.logger.warn("relay moved from GPIO5 to config pin %s", relay_number)
        self.state.set_device(
            name=self.config["device"]["name"],
            model=DEVICE_MODEL,
            firmware=FIRMWARE,
            version=VERSION,
            source="device",
        )
        self.state.set("security", {
            "pin_required": bool(self.config["security"].get("require_pin"))
        })

        i2c = machine.SoftI2C(
            scl=machine.Pin(self.config["pins"]["i2c_scl"]),
            sda=machine.Pin(self.config["pins"]["i2c_sda"]),
            freq=100000,
        )
        adc = machine.ADC(machine.Pin(self.config["pins"]["soil_adc"]))
        try:
            adc.atten(machine.ADC.ATTN_11DB)
        except Exception:
            pass

        sensors = {
            "soil": SoilSensor(adc, lambda: self.config["calibration"], self.clock),
            "air": SHT31(i2c),
            "light": BH1750(i2c),
        }
        self.manager = SensorManager(
            sensors,
            self.state,
            self.logger,
            stale_s=int(self.config["irrigation"].get("sensor_stale_s", 90)),
        )
        self.history = HistoryStore(
            "/data/history",
            self.logger,
            retention_days=int(self.config["sampling"].get("history_days", 7)),
        )
        self.history.load()

        self.controller = IrrigationController(
            self.relay,
            self.config,
            self.clock,
            self.state,
            IrrigationHistory(),
            self.logger,
        )
        self.api = DeviceApi(
            self.state,
            self.controller,
            self.config_store,
            self.history,
            self.config,
            self.clock,
            self.logger,
            source="device",
        )

        wlan = network.WLAN(network.STA_IF)
        self.network = NetworkManager(wlan, self.state, self.logger, self.clock)
        wifi = kv.read_json("wifi.json", {}) or {}
        self.network.set_credentials(wifi.get("ssid", ""), wifi.get("password", ""))

        self.web = WebServer(
            self.api,
            "/web/static",
            host="0.0.0.0",
            port=80,
            logger=self.logger,
        )
        self.logger.info("build complete")
        return self

    async def sensor_loop(self):
        last_history = 0
        ticks = 0
        while True:
            now = self.clock.now()
            readings = self.manager.poll(now)
            profile = get_profile(self.config["plant"].get("profile", "general"))
            result = evaluate(
                readings,
                profile,
                now,
                stale_s=int(self.config["irrigation"].get("sensor_stale_s", 90)),
            )
            self.state.set_suitability(result, now)
            self.state.set_device(
                time_synced=bool(getattr(self.clock, "synced", False)),
                now=now,
                now_local=format_local(now, self.config["device"]["timezone_offset"])
                if getattr(self.clock, "synced", False)
                else "",
            )
            interval = int(self.config["sampling"].get("history_interval_s", 300))
            if now - last_history >= interval:
                point = _history_point(readings, result, now)
                self.history.append(point, now)
                last_history = now
            try:
                self.state.set_uptime(time.ticks_diff(time.ticks_ms(), self.boot_ticks) // 1000)
            except Exception:
                pass
            ticks += 1
            if ticks % 20 == 0:
                gc.collect()
            if self.wdt:
                self.wdt.feed()
            await asyncio.sleep(int(self.config["sampling"].get("interval_s", 30)))

    async def control_loop(self):
        while True:
            now = self.clock.now()
            self.controller.tick(now, self.manager.get("soil") if self.manager else None)
            self.state.set_meta(now)
            if self.wdt:
                self.wdt.feed()
            await asyncio.sleep(1)

    async def network_loop(self):
        while True:
            self.network.tick(self.clock.now())
            await asyncio.sleep(5)

    async def _guard(self, name, runner):
        """Keep one task's failure from taking down sensing or irrigation."""
        while True:
            try:
                await runner()
            except Exception as exc:
                self.logger.error("%s task failed: %s", name, exc)
                await asyncio.sleep(5)

    async def run(self):
        self.build()
        tasks = [
            asyncio.create_task(self._guard("sensor", self.sensor_loop)),
            asyncio.create_task(self._guard("control", self.control_loop)),
            asyncio.create_task(self._guard("network", self.network_loop)),
        ]
        if self.config.get("features", {}).get("web", True):
            tasks.append(asyncio.create_task(self._guard("web", self.web.serve_forever)))
        await asyncio.gather(*tasks)


def _history_point(readings, suitability, now):
    def value(name):
        reading = readings.get(name)
        return round(reading.value, 2) if reading is not None and reading.valid else None

    return {
        "ts": int(now),
        "temp": value("air_temp"),
        "humidity": value("air_humidity"),
        "soil": value("soil"),
        "light": value("light"),
        "suitability": suitability.get("score") if suitability else None,
    }


def main():
    app = Application()
    try:
        try:
            asyncio.run(app.run())
        except AttributeError:
            asyncio.get_event_loop().run_until_complete(app.run())
    except Exception as exc:
        app.logger.error("fatal: %s", exc)
        if app.relay is not None:
            app.relay.off("fatal")
        try:
            sys.print_exception(exc)
        except Exception:
            pass
        time.sleep(3)
        machine.reset()


if __name__ == "__main__":
    main()
