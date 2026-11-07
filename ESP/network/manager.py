"""Wi-Fi auto-connect and provisioning state machine.

Rules from AGENT.md:
- never block the main loop;
- retry the saved network, then stop after five failures and wait for
  provisioning;
- only replace the saved credentials after the new network is verified;
- never expose the password in status/logs;
- keep sensing/irrigation running while the network is down.
"""

STATUS_TEXT = {
    1002: "wrong_password",
    1003: "no_ap_found",
    1004: "connect_failed",
}

STATE_UNCONFIGURED = "unconfigured"
STATE_IDLE = "idle"
STATE_CONNECTING = "connecting"
STATE_CONNECTED = "connected"
STATE_FAILED = "failed"
STATE_PROVISIONING = "provisioning"


class NetworkManager:
    def __init__(self, wlan, store, state, logger, clock):
        self.wlan = wlan
        self.store = store
        self.state_store = state
        self.logger = logger
        self.clock = clock
        self.saved = store.load() or {}
        self.pending = None
        self.ssid = self.saved.get("ssid", "")
        self.password = self.saved.get("password", "")
        self.attempts = 0
        self.last_attempt = -999
        self.connect_started = None
        self.last_error = None
        self.state_name = STATE_UNCONFIGURED if not self.ssid else STATE_IDLE
        self.max_attempts = 5
        self.retry_interval_s = 15
        self.connect_timeout_s = 20
        self._was_connected = False

    # ------------------------------------------------------------------ boot
    def start(self):
        if self.ssid:
            self._attempt(self.clock.now())
        else:
            self.state_name = STATE_UNCONFIGURED
            self.publish()

    # ------------------------------------------------------------------ loop
    def tick(self, now):
        try:
            connected = bool(self.wlan.isconnected())
        except Exception as exc:
            self.last_error = "wlan_error: %s" % exc
            self.state_name = STATE_FAILED
            self.publish()
            return

        if connected:
            self._on_connected(now)
            return

        if self.state_name == STATE_CONNECTED:
            # The AP dropped (or the link was lost) after a successful join.
            self.state_name = STATE_FAILED
            self.attempts = 0
            self.last_attempt = int(now)
            self.last_error = "disconnected"
            self.logger.warn("wifi disconnected")

        if self.state_name == STATE_CONNECTING:
            if self.connect_started is not None and (now - self.connect_started) >= self.connect_timeout_s:
                self._fail("timeout", now)
            else:
                self._check_status(now)
            self.publish()
            return

        if self.state_name == STATE_PROVISIONING:
            self.publish()
            return

        if self.ssid and self.attempts < self.max_attempts and (now - self.last_attempt) >= self.retry_interval_s:
            self._attempt(now)
        self.publish()

    def _check_status(self, now):
        try:
            code = self.wlan.status()
        except Exception as exc:
            self._fail("status_error: %s" % exc, now)
            return
        if code in STATUS_TEXT:
            self._fail(STATUS_TEXT[code], now)

    def _on_connected(self, now):
        if not self._was_connected:
            self.logger.info("wifi connected")
        self._was_connected = True
        self.attempts = 0
        self.last_error = None
        if self.pending:
            # Only now is the new network verified; replace the old config.
            self.store.save(self.pending["ssid"], self.pending["password"])
            self.saved = {
                "ssid": self.pending["ssid"],
                "password": self.pending["password"],
            }
            self.ssid = self.pending["ssid"]
            self.password = self.pending["password"]
            self.pending = None
            self.logger.info("wifi credentials saved")
        self.state_name = STATE_CONNECTED
        self.publish()

    def _attempt(self, now):
        self.attempts += 1
        self.last_attempt = int(now)
        self.connect_started = int(now)
        self.state_name = STATE_CONNECTING
        try:
            self.wlan.active(True)
            self.wlan.connect(self.ssid, self.password)
            self.logger.info("wifi attempt %d for %s", self.attempts, self.ssid)
        except Exception as exc:
            self._fail("connect_error: %s" % exc, now)
        self.publish()

    def _fail(self, reason, now):
        self.last_error = reason
        self.state_name = STATE_FAILED
        self.logger.warn("wifi attempt failed: %s", reason)
        if self.attempts >= self.max_attempts:
            self.state_name = STATE_PROVISIONING
            self.logger.warn("wifi retry limit reached; provisioning required")
        self.publish()

    # ----------------------------------------------------------- provisioning
    def connect(self, ssid, password):
        ssid = (ssid or "").strip()
        password = password or ""
        if not ssid:
            return False, "SSID_REQUIRED"
        if len(ssid) > 32:
            return False, "SSID_TOO_LONG"
        if len(password) > 64:
            return False, "PASSWORD_TOO_LONG"
        self.pending = {"ssid": ssid, "password": password}
        self.ssid = ssid
        self.password = password
        self.attempts = 0
        self.last_attempt = -999
        self.last_error = None
        self.state_name = STATE_IDLE
        self._attempt(self.clock.now())
        return True, None

    def cancel_provisioning(self):
        if not self.pending:
            return False
        self.pending = None
        self.ssid = self.saved.get("ssid", "")
        self.password = self.saved.get("password", "")
        self.attempts = 0
        self.state_name = STATE_UNCONFIGURED if not self.ssid else STATE_IDLE
        self.last_error = None
        self.publish()
        return True

    def forget(self):
        self.store.clear()
        self.saved = {}
        self.pending = None
        self.ssid = ""
        self.password = ""
        self.attempts = 0
        self.state_name = STATE_UNCONFIGURED
        self.last_error = None
        try:
            self.wlan.disconnect()
        except Exception:
            pass
        self.publish()

    def scan(self, limit=20):
        try:
            self.wlan.active(True)
            raw = self.wlan.scan()
        except Exception as exc:
            self.last_error = "scan_error: %s" % exc
            return []
        found = {}
        for item in raw:
            ssid = item[0]
            if isinstance(ssid, bytes):
                ssid = ssid.decode("utf-8", "replace")
            if not ssid:
                continue
            rssi = item[3]
            current = found.get(ssid)
            if current is None or (rssi or -999) > (current.get("rssi") or -999):
                found[ssid] = {
                    "ssid": ssid,
                    "rssi": rssi,
                    "security": item[4],
                    "secure": bool(item[4]),
                }
        result = list(found.values())
        result.sort(key=lambda row: row.get("rssi") or -999, reverse=True)
        return result[:limit]

    # ------------------------------------------------------------------ view
    def status(self):
        ip = ""
        rssi = None
        try:
            if self.wlan.isconnected():
                config = self.wlan.ifconfig()
                ip = config[0] if config else ""
                try:
                    rssi = self.wlan.status("rssi")
                except Exception:
                    rssi = None
        except Exception:
            pass
        return {
            "wifi": self.state_name,
            "status": self.state_name,
            "ssid": self.ssid,
            "saved_ssid": self.saved.get("ssid", ""),
            "pending_ssid": self.pending["ssid"] if self.pending else "",
            "ip": ip,
            "rssi": rssi,
            "attempts": self.attempts,
            "last_error": self.last_error,
            "provisioning": self.state_name == STATE_PROVISIONING,
        }

    def publish(self):
        self.state_store.set_network(self.status())
