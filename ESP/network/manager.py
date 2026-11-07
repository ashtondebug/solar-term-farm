"""Non-blocking Wi-Fi station state machine.

Provisioning through the TJC screen is a later milestone.  For M1 the
credentials can be placed in ``/data/wifi.json``; after five failed attempts
the manager stops retrying and reports ``provisioning`` so the screen work can
take over without changing the core loop.
"""

import time


class NetworkManager:
    def __init__(self, wlan, state, logger, clock):
        self.wlan = wlan
        self.state_store = state
        self.logger = logger
        self.clock = clock
        self.ssid = ""
        self.password = ""
        self.attempts = 0
        self.last_attempt = -999
        self.mode = "offline"
        self.last_error = None
        self._configured = False

    def set_credentials(self, ssid, password):
        self.ssid = ssid or ""
        self.password = password or ""
        self._configured = bool(self.ssid)

    def start(self):
        if not self._configured:
            self.mode = "unconfigured"
            self.publish()
            return
        try:
            self.wlan.active(True)
        except Exception as exc:
            self.last_error = str(exc)
            self.mode = "error"
        self.tick(self.clock.now())

    def tick(self, now):
        if not self._configured:
            self.mode = "unconfigured"
            self.publish()
            return
        try:
            connected = self.wlan.isconnected()
        except Exception as exc:
            self.last_error = str(exc)
            self.mode = "error"
            self.publish()
            return

        if connected:
            self.attempts = 0
            self.mode = "connected"
            self.publish()
            return

        if self.attempts >= 5:
            self.mode = "provisioning"
            self.publish()
            return

        if (now - self.last_attempt) >= 15:
            self._attempt(now)

    def _attempt(self, now):
        self.last_attempt = int(now)
        self.attempts += 1
        self.mode = "connecting"
        try:
            self.wlan.active(True)
            self.wlan.connect(self.ssid, self.password)
            self.logger.info("wifi connect attempt %d for %s", self.attempts, self.ssid)
        except Exception as exc:
            self.last_error = str(exc)
            self.mode = "error"
            self.logger.warn("wifi connect failed: %s", exc)
        self.publish()

    def scan(self):
        try:
            raw = self.wlan.scan()
        except Exception as exc:
            self.last_error = str(exc)
            return []
        results = []
        for item in raw:
            ssid = item[0]
            if isinstance(ssid, bytes):
                ssid = ssid.decode("utf-8", "replace")
            results.append({"ssid": ssid, "rssi": item[3], "security": item[4]})
        results.sort(key=lambda row: row.get("rssi") or -999, reverse=True)
        return results

    def status(self):
        ip = ""
        ssid = self.ssid
        rssi = None
        try:
            if self.wlan.isconnected():
                config = self.wlan.ifconfig()
                ip = config[0] if config else ""
                try:
                    ssid = self.wlan.config("essid") or ssid
                except Exception:
                    pass
                try:
                    rssi = self.wlan.status("rssi")
                except Exception:
                    rssi = None
        except Exception:
            pass
        return {
            "wifi": self.mode,
            "status": self.mode,
            "ssid": ssid,
            "ip": ip,
            "rssi": rssi,
            "attempts": self.attempts,
            "last_error": self.last_error,
        }

    def publish(self):
        self.state_store.set_network(self.status())
