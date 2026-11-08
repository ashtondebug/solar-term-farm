"""Secure-ish storage for Wi-Fi credentials.

The ESP32-S3 has no secure element.  The file is kept out of the public API
and logs, written atomically, and never returned by ``status``.  Physical
access to the flash remains a documented limitation.
"""

import os


class WifiStore:
    def __init__(self, kv, logger=None):
        self.kv = kv
        self.logger = logger

    def load(self):
        data = self.kv.read_json("wifi.json", {})
        if not isinstance(data, dict):
            return {}
        ssid = data.get("ssid", "")
        password = data.get("password", "")
        if not isinstance(ssid, str) or not isinstance(password, str) or not ssid:
            return {}
        return {"ssid": ssid, "password": password}

    def save(self, ssid, password):
        self.kv.write_json("wifi.json", {"ssid": ssid, "password": password})

    def clear(self):
        try:
            os.remove(self.kv.path("wifi.json"))
        except OSError:
            pass

    def exists(self):
        return self.kv.exists("wifi.json")
