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

# Reserve the Wi-Fi stack before importing the full application.  The 24-term
# content is large; if Wi-Fi is created after those modules, MicroPython can
# raise "WiFi Out of Memory" even though the Python heap still looks free.
_WLAN = network.WLAN(network.STA_IF)

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
from netmgr.manager import NetworkManager
from netmgr.store import WifiStore
from sensors.bh1750 import BH1750
from sensors.i2c_bus import RecoveringI2C
from sensors.manager import SensorManager
from sensors.sht31 import SHT31
from sensors.soil import SoilSensor
from storage.config_store import ConfigStore
from storage.history_store import HistoryStore
from storage.kvstore import KVStore
from suitability.model import evaluate
from suitability.plants import get_profile
from suitability.store import PlantProfileStore
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
        self.plant_store = PlantProfileStore(kv, self.logger)
        try:
            self.plant_store.load()
        except Exception as exc:
            self.logger.warn("plant profile load failed: %s", exc)
        self.config_store = ConfigStore(kv, self.logger)
        self.config = self.config_store.load()
        relay_number = int(self.config["pins"].get("relay", 5))
        feedback_number = self.config["pins"].get("relay_feedback")
        if relay_number != 5 or feedback_number is not None:
            reviewed_pin = machine.Pin(relay_number, machine.Pin.OUT, value=0)
            feedback_pin = None
            if feedback_number is not None:
                feedback_pin = machine.Pin(
                    int(feedback_number), machine.Pin.IN, machine.Pin.PULL_UP
                )
            self.relay = Relay(
                reviewed_pin,
                active_high=True,
                logger=self.logger,
                feedback_pin=feedback_pin,
                feedback_active_low=True,
            )
            if relay_number != 5:
                self.logger.warn("relay moved from GPIO5 to config pin %s", relay_number)
            if feedback_pin is not None:
                self.logger.info("relay feedback on GPIO%s", feedback_number)
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

        # The Wi-Fi stack was reserved at import time; reuse that object.
        gc.collect()
        wlan = _WLAN
        self.network = NetworkManager(
            wlan,
            WifiStore(kv, self.logger, use_code_defaults=True),
            self.state,
            self.logger,
            self.clock,
        )
        self.network.start()

        i2c = RecoveringI2C(
            scl=self.config["pins"]["i2c_scl"],
            sda=self.config["pins"]["i2c_sda"],
            freq=100000,
            logger=self.logger,
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
            plant_store=self.plant_store,
            recompute=self.recompute_suitability,
        )

        self.web = WebServer(
            self.api,
            "/web/static",
            host="0.0.0.0",
            port=80,
            logger=self.logger,
        )

        self.tft = None
        self.button = None
        if self.config.get("tft", {}).get("enabled"):
            try:
                from tft.display import TftDisplay
                from tft.ili9341 import ILI9341

                tft_cfg = self.config["tft"]
                pins = self.config["pins"]
                spi = machine.SPI(
                    2,
                    baudrate=int(tft_cfg.get("freq", 20000000)),
                    polarity=0,
                    phase=0,
                    sck=machine.Pin(pins["tft_sck"]),
                    mosi=machine.Pin(pins["tft_sda"]),
                )
                driver = ILI9341(
                    spi,
                    cs=pins["tft_cs"],
                    dc=pins["tft_dc"],
                    rst=pins["tft_rst"],
                    width=240,
                    height=320,
                    rotation=int(tft_cfg.get("rotation", 0)),
                )
                self.tft = TftDisplay(driver, self.state, self.clock, self.logger)
                self.logger.info(
                    "tft ILI9341 SCK%s/SDA%s CS%s DC%s RST%s",
                    pins["tft_sck"],
                    pins["tft_sda"],
                    pins["tft_cs"],
                    pins["tft_dc"],
                    pins["tft_rst"],
                )
            except Exception as exc:
                self.logger.warn("tft init failed: %s", exc)

        if self.config.get("button", {}).get("enabled"):
            try:
                from button import PumpButton

                button_cfg = self.config["button"]
                button_pin = machine.Pin(
                    self.config["pins"]["button"],
                    machine.Pin.IN,
                    machine.Pin.PULL_DOWN,
                )
                self.button = PumpButton(
                    button_pin,
                    self.controller,
                    self.clock,
                    self.logger,
                    active_high=bool(button_cfg.get("active_high", True)),
                    debounce_ms=int(button_cfg.get("debounce_ms", 50)),
                )
                self.logger.info(
                    "button on GPIO%s active-high", self.config["pins"]["button"]
                )
            except Exception as exc:
                self.logger.warn("button init failed: %s", exc)

        self.logger.info("build complete")
        return self

    async def sensor_loop(self):
        last_history = 0
        ticks = 0
        while True:
            now = self.clock.now()
            readings = self.manager.poll(now)
            plant = self.config["plant"]
            profile = get_profile(
                plant.get("profile", "general"),
                plant.get("stage", "growth"),
                plant.get("weights"),
            )
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

    def recompute_suitability(self):
        """Re-evaluate using cached readings after a profile/config change."""
        if self.manager is None:
            return
        now = self.clock.now()
        plant = self.config["plant"]
        profile = get_profile(
            plant.get("profile", "general"),
            plant.get("stage", "growth"),
            plant.get("weights"),
        )
        result = evaluate(
            self.manager.readings,
            profile,
            now,
            stale_s=int(self.config["irrigation"].get("sensor_stale_s", 90)),
        )
        self.state.set_suitability(result, now)

    async def run(self):
        self.build()
        tasks = [
            asyncio.create_task(self._guard("sensor", self.sensor_loop)),
            asyncio.create_task(self._guard("control", self.control_loop)),
            asyncio.create_task(self._guard("network", self.network_loop)),
        ]
        if self.config.get("features", {}).get("web", True):
            tasks.append(asyncio.create_task(self._guard("web", self.web.serve_forever)))
        if self.tft is not None:
            tasks.append(asyncio.create_task(self._guard("tft", self.tft.run)))
        if self.button is not None:
            tasks.append(asyncio.create_task(self._guard("button", self.button.run)))
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
