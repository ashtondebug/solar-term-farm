import unittest

import _bootstrap  # noqa: F401
from display.protocol import parse_line, text_command
from display.screen import ScreenController


class FakeClock:
    def __init__(self, now=1000):
        self.value = now

    def now(self):
        return self.value


class FakeTransport:
    def __init__(self):
        self.sent = []
        self.lines = []

    def read_lines(self):
        lines = self.lines
        self.lines = []
        return lines

    def send(self, command):
        self.sent.append(command)


class FakeConfigStore:
    def __init__(self, config):
        self.config = config

    def save(self, config):
        self.config = config


class FakeController:
    def __init__(self):
        self.calls = []
        self.mode = "auto"

    def request(self, action, source, request_id, now):
        self.calls.append((action, source, request_id, now))
        return {"ok": True}

    def set_mode(self, mode):
        self.mode = mode
        return True, None

    def publish(self, now):
        pass


class FakeNetwork:
    def scan(self, limit=20):
        return [{"ssid": "TestWiFi", "rssi": -42}]

    def connect(self, ssid, password):
        return True, None


class FakeState:
    data = {
        "device": {"now_local": "10:20"},
        "sensors": {},
        "irrigation": {"pump": False, "mode": "auto", "state": "idle", "remaining_s": 0},
        "network": {"wifi": "connected", "ip": "192.168.1.2"},
        "solar_term": {"name": "立冬"},
        "suitability": {"score": 80},
    }


class DisplayTests(unittest.IsolatedAsyncioTestCase):
    def make_screen(self, require_pin=False, pin="123456"):
        config = {"security": {"require_pin": require_pin, "pin": pin}, "irrigation": {}}
        transport = FakeTransport()
        controller = FakeController()
        screen = ScreenController(
            transport,
            FakeState(),
            config,
            FakeConfigStore(config),
            controller,
            FakeNetwork(),
            FakeClock(),
            None,
        )
        return screen, transport, controller

    def test_parse_protocol(self):
        self.assertEqual(parse_line("PING")["cmd"], "PING")
        self.assertEqual(parse_line("CMD|start")["action"], "start")
        self.assertEqual(parse_line("WIFI|CONNECT|MyNet|pa|ss")["password"], "pa|ss")
        with self.assertRaises(ValueError):
            parse_line("CMD|explode")
        with self.assertRaises(ValueError):
            parse_line("PAGE|unknown")

    def test_text_command_escapes(self):
        self.assertEqual(text_command("t_temp", 'a"b'), 't_temp.txt="a\'b"')

    async def test_auth_and_control(self):
        screen, transport, controller = self.make_screen(require_pin=True)
        await screen.handle_line("CMD|start")
        self.assertEqual(controller.calls, [])
        await screen.handle_line("AUTH|bad")
        self.assertIn('t_status.txt="PIN_INVALID"', transport.sent)
        await screen.handle_line("AUTH|123456")
        await screen.handle_line("CMD|start")
        self.assertEqual(controller.calls[0][0], "start")
        self.assertEqual(controller.calls[0][1], "screen")

    async def test_wifi_scan(self):
        screen, transport, _controller = self.make_screen()
        await screen.handle_line("WIFI|SCAN")
        self.assertIn('t_wifi0.txt="TestWiFi  -42 dBm"', transport.sent)
        self.assertIn('t_wifi_count.txt="1"', transport.sent)


if __name__ == "__main__":
    unittest.main()
