import json
import os
import tempfile
import unittest

import _bootstrap  # noqa: F401
from core.log import Logger
from core.state import DeviceState
from fakes.hardware import FakeClock
from fakes.wifi import FakeWlan, MemoryWifiStore
from network.manager import (
    STATE_CONNECTED,
    STATE_PROVISIONING,
    STATE_UNCONFIGURED,
    NetworkManager,
)
from network.store import WifiStore
from storage.kvstore import KVStore


def build(store_data=None, networks=None):
    clock = FakeClock(1000)
    state = DeviceState()
    wlan = FakeWlan(networks)
    store = MemoryWifiStore(store_data or {})
    logger = Logger("test", "error", sink=lambda line: None)
    manager = NetworkManager(wlan, store, state, logger, clock)
    return manager, wlan, store, state, clock


class NetworkManagerTests(unittest.TestCase):
    def test_unconfigured(self):
        manager, wlan, store, state, clock = build()
        manager.start()
        self.assertEqual(manager.status()["status"], STATE_UNCONFIGURED)
        self.assertEqual(wlan.connect_calls, [])

    def test_connect_success_saves_only_after_verification(self):
        manager, wlan, store, state, clock = build()
        ok, error = manager.connect("Home", "secret-pass")
        self.assertTrue(ok)
        self.assertIsNone(error)
        self.assertEqual(store.data, {})  # not saved before verification

        wlan.connected = True
        wlan.status_code = 1010
        manager.tick(1000)
        self.assertEqual(manager.status()["status"], STATE_CONNECTED)
        self.assertEqual(store.data, {"ssid": "Home", "password": "secret-pass"})
        self.assertEqual(manager.status()["ip"], "192.168.1.50")

    def test_password_never_in_status(self):
        manager, wlan, store, state, clock = build()
        manager.connect("Home", "top-secret")
        payload = json.dumps(manager.status())
        self.assertNotIn("top-secret", payload)
        self.assertNotIn("password", payload)

    def test_wrong_password_and_retry_limit(self):
        manager, wlan, store, state, clock = build()
        manager.connect("Home", "bad")
        now = 1000
        for _ in range(5):
            wlan.status_code = 1002
            manager.tick(now)
            now += 16
            wlan.status_code = 1002
            manager.tick(now)
        self.assertEqual(manager.status()["status"], STATE_PROVISIONING)
        self.assertEqual(manager.status()["last_error"], "wrong_password")
        self.assertEqual(store.data, {})

    def test_cancel_restores_saved_network(self):
        manager, wlan, store, state, clock = build({"ssid": "Old", "password": "old-pass"})
        manager.start()
        manager.connect("New", "new-pass")
        wlan.status_code = 1002
        manager.tick(1000)
        self.assertEqual(manager.status()["pending_ssid"], "New")
        self.assertTrue(manager.cancel_provisioning())
        self.assertEqual(manager.status()["ssid"], "Old")
        self.assertEqual(store.data["ssid"], "Old")

    def test_scan_deduplicates_and_sorts(self):
        networks = [
            (b"Home", b"aa", 6, -40, 3, 0),
            (b"Cafe", b"bb", 1, -70, 0, 0),
            (b"Home", b"cc", 11, -50, 3, 0),
            (b"", b"dd", 1, -20, 0, 0),
        ]
        manager, wlan, store, state, clock = build(networks=networks)
        result = manager.scan()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["ssid"], "Home")
        self.assertEqual(result[0]["rssi"], -40)
        self.assertEqual(result[1]["ssid"], "Cafe")


class WifiStoreTests(unittest.TestCase):
    def test_roundtrip_and_clear(self):
        root = tempfile.mkdtemp(prefix="agri-wifi-")
        store = WifiStore(KVStore(root))
        store.save("Home", "pass")
        self.assertEqual(store.load(), {"ssid": "Home", "password": "pass"})
        store.clear()
        self.assertEqual(store.load(), {})
        self.assertFalse(os.path.exists(os.path.join(root, "wifi.json")))


if __name__ == "__main__":
    unittest.main()
