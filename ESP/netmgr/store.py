"""Secure-ish storage for Wi-Fi credentials.

The ESP32-S3 has no secure element.  The file is kept out of the public API
and logs, written atomically, and never returned by ``status``.  Physical
access to the flash remains a documented limitation.
"""

import os


class WifiStore:
    def __init__(self, kv, logger=None, use_code_defaults=False):
        self.kv = kv
        self.logger = logger
        self.use_code_defaults = bool(use_code_defaults)

    def load(self):
        data = self.kv.read_json("wifi.json", {})
        if isinstance(data, dict):
            ssid = data.get("ssid", "")
            password = data.get("password", "")
            if isinstance(ssid, str) and isinstance(password, str) and ssid:
                return {"ssid": ssid, "password": password}
        # Local development fallback. The real file is ignored by Git; only
        # wifi_secrets.example.py with placeholders is public.
        if not self.use_code_defaults:
            return {}
        try:
            from wifi_secrets import WIFI_PASSWORD, WIFI_SSID
        except ImportError:
            return {}
        if isinstance(WIFI_SSID, str) and isinstance(WIFI_PASSWORD, str) and WIFI_SSID:
            return {"ssid": WIFI_SSID, "password": WIFI_PASSWORD}
        return {}

    def save(self, ssid, password):
        self.kv.write_json("wifi.json", {"ssid": ssid, "password": password})

    def clear(self):
        try:
            os.remove(self.kv.path("wifi.json"))
        except OSError:
            pass

    def exists(self):
        return self.kv.exists("wifi.json")
