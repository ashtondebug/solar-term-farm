"""Fake Wi-Fi stack for the provisioning state-machine tests."""


class FakeWlan:
    def __init__(self, networks=None):
        self.active_flag = False
        self.connected = False
        self.status_code = 1000
        self.connect_calls = []
        self.networks = list(networks or [])
        self.disconnected = 0

    def active(self, value=None):
        if value is None:
            return self.active_flag
        self.active_flag = bool(value)

    def isconnected(self):
        return self.connected

    def connect(self, ssid, password):
        self.connect_calls.append((ssid, password))
        self.connected = False
        self.status_code = 1001

    def status(self, parameter=None):
        if parameter == "rssi":
            return -55
        return self.status_code

    def ifconfig(self):
        return ("192.168.1.50", "255.255.255.0", "192.168.1.1", "8.8.8.8")

    def scan(self):
        return list(self.networks)

    def disconnect(self):
        self.connected = False
        self.disconnected += 1


class MemoryWifiStore:
    def __init__(self, data=None):
        self.data = dict(data or {})

    def load(self):
        return dict(self.data)

    def save(self, ssid, password):
        self.data = {"ssid": ssid, "password": password}

    def clear(self):
        self.data = {}

    def exists(self):
        return bool(self.data)
