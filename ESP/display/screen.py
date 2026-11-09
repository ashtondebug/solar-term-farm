"""Screen state bridge.

The TJC is a client: it receives HMI component updates and submits short
commands.  It never touches the relay, sensor bus or Wi-Fi driver directly.
"""

import asyncio

from config import ensure_pin
from display.protocol import parse_line, text_command

AUTH_SECONDS = 300
STATUS_INTERVAL_S = 2
WIFI_ROWS = 6

WIFI_LABELS = {
    "connected": "已连接",
    "connecting": "连接中",
    "failed": "连接失败",
    "provisioning": "待配网",
    "unconfigured": "未配置",
    "offline": "离线",
    "idle": "待连接",
}


class ScreenController:
    def __init__(self, transport, state, config, config_store, controller, network, clock, logger):
        self.transport = transport
        self.state = state
        self.config = config
        self.config_store = config_store
        self.controller = controller
        self.network = network
        self.clock = clock
        self.logger = logger
        self.page = "overview"
        self.auth_until = 0
        self.last_values = {}

    # ------------------------------------------------------------------ I/O
    def send(self, command):
        try:
            self.transport.send(command)
        except Exception as exc:
            if self.logger:
                self.logger.warn("screen send failed: %s", exc)

    def set_text(self, component, value):
        text = "" if value is None else str(value)
        if self.last_values.get(component) == text:
            return
        self.last_values[component] = text
        self.send(text_command(component, text))

    def set_page(self, page):
        self.page = page
        self.send("page %s" % page)

    # ------------------------------------------------------------- commands
    def _auth_required(self):
        return bool(self.config.get("security", {}).get("require_pin"))

    def _authorized(self):
        if not self._auth_required():
            return True
        return self.clock.now() < self.auth_until

    def _require_auth(self):
        if self._authorized():
            return True
        self.set_text("t_status", "需要 PIN")
        return False

    def _error(self, code):
        self.set_text("t_status", str(code))
        if self.logger:
            self.logger.warn("screen command rejected: %s", code)

    async def handle_line(self, line):
        try:
            message = parse_line(line)
        except ValueError as exc:
            self._error(str(exc))
            return
        if message is None:
            return
        command = message["cmd"]
        if command == "AUTH":
            expected = self.config.get("security", {}).get("pin", "")
            if self._auth_required() and message["pin"] != expected:
                self._error("PIN_INVALID")
                return
            self.auth_until = self.clock.now() + AUTH_SECONDS
            self.set_text("t_auth", "已解锁")
            self.set_text("t_status", "PIN 已通过")
            return
        if command == "PING":
            self.set_text("t_status", "PONG")
            return
        if command == "PAGE":
            self.page = message["page"]
            self.set_text("t_page", self.page)
            return
        if command == "CMD":
            if not self._require_auth():
                return
            request_id = "screen-%d" % self.clock.now()
            result = self.controller.request(message["action"], "screen", request_id, self.clock.now())
            if result.get("ok"):
                self.set_text("t_status", "已执行")
            else:
                self._error(result.get("code", "CONTROL_FAILED"))
            self.push_status(force=True)
            return
        if command == "MODE":
            if not self._require_auth():
                return
            ok, error = self.controller.set_mode(message["mode"])
            if not ok:
                self._error(error)
                return
            try:
                self.config_store.save(self.config)
            except Exception as exc:
                self._error("CONFIG_SAVE_FAILED")
                if self.logger:
                    self.logger.warn("screen config save failed: %s", exc)
            self.set_text("t_status", "模式已更新")
            self.push_status(force=True)
            return
        if command == "SET":
            if not self._require_auth():
                return
            self.config["irrigation"]["soil_threshold"] = message["value"]
            try:
                self.config_store.save(self.config)
            except Exception as exc:
                self._error("CONFIG_SAVE_FAILED")
                if self.logger:
                    self.logger.warn("screen config save failed: %s", exc)
                return
            self.controller.publish(self.clock.now())
            self.set_text("t_status", "阈值已更新")
            self.push_status(force=True)
            return
        if command == "WIFI":
            if message["action"] == "SCAN":
                await self.scan_wifi()
            elif message["action"] == "CONNECT":
                if not self._require_auth():
                    return
                ok, error = self.network.connect(message["ssid"], message["password"])
                if not ok:
                    self._error(error)
                else:
                    self.set_text("t_status", "正在连接 WiFi")
                self.push_status(force=True)
            return
        if command == "PIN":
            if not self._require_auth():
                return
            pin = self.config.get("security", {}).get("pin", "")
            if not pin:
                pin = ensure_pin(self.config)
                try:
                    self.config_store.save(self.config)
                except Exception as exc:
                    if self.logger:
                        self.logger.warn("screen PIN save failed: %s", exc)
            self.set_text("t_pin", pin)
            self.set_text("t_status", "PIN 已显示")
            return
        self._error("UNKNOWN_COMMAND")

    async def scan_wifi(self):
        self.set_text("t_status", "正在扫描 WiFi")
        try:
            rows = self.network.scan(WIFI_ROWS)
        except Exception as exc:
            if self.logger:
                self.logger.warn("screen wifi scan failed: %s", exc)
            rows = []
        for index in range(WIFI_ROWS):
            if index < len(rows):
                row = rows[index]
                label = "%s  %s dBm" % (row.get("ssid", ""), row.get("rssi", ""))
            else:
                label = ""
            self.set_text("t_wifi%d" % index, label)
        self.set_text("t_wifi_count", str(len(rows)))
        self.set_text("t_status", "扫描完成")

    # --------------------------------------------------------------- state
    def _reading(self, name):
        sensors = self.state.data.get("sensors", {})
        item = sensors.get(name) if isinstance(sensors, dict) else None
        if not item or not item.get("valid"):
            return "—"
        value = item.get("value")
        return "—" if value is None else value

    def _number(self, value):
        if value is None:
            return "—"
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return str(value)
        return "%g" % value

    def push_status(self, force=False):
        data = self.state.data
        device = data.get("device", {})
        network = data.get("network", {})
        solar = data.get("solar_term") or {}
        irrigation = data.get("irrigation", {})
        suitability = data.get("suitability", {})
        self.set_text("t_time", device.get("now_local") or "--:--")
        self.set_text("t_temp", self._number(self._reading("air_temp")))
        self.set_text("t_hum", self._number(self._reading("air_humidity")))
        self.set_text("t_soil", self._number(self._reading("soil")))
        self.set_text("t_light", self._number(self._reading("light")))
        self.set_text("t_score", self._number(suitability.get("score")))
        self.set_text("t_pump", "运行" if irrigation.get("pump") else "停止")
        self.set_text("t_mode", "自动" if irrigation.get("mode") == "auto" else "手动")
        self.set_text("t_remain", "%ss" % irrigation.get("remaining_s", 0))
        self.set_text("t_threshold", self._number(irrigation.get("threshold")))
        self.set_text("t_state", irrigation.get("state", "idle"))
        self.set_text("t_fault", "FAULT" if irrigation.get("state") == "fault" else "")
        self.set_text("t_term", solar.get("name") or "—")
        self.set_text("t_wifi", WIFI_LABELS.get(network.get("wifi"), network.get("wifi", "离线")))
        self.set_text("t_wifi_detail", WIFI_LABELS.get(network.get("wifi"), network.get("wifi", "离线")))
        self.set_text("t_ip", network.get("ip") or "—")
        self.set_text("t_auth", "已解锁" if self._authorized() else "只读")
        self.set_text("t_page", self.page)

    async def run(self):
        self.set_page("overview")
        self.push_status(force=True)
        last_status = 0
        while True:
            for line in self.transport.read_lines():
                await self.handle_line(line)
            now = self.clock.now()
            if now - last_status >= STATUS_INTERVAL_S:
                self.push_status()
                last_status = now
            await asyncio.sleep_ms(50)
