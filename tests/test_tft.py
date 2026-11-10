"""Host tests for the TFT formatting helpers."""

import unittest

import _bootstrap  # noqa: F401
from tft.format import clock_text, format_value


class TftFormatTests(unittest.TestCase):
    def test_value(self):
        self.assertEqual(format_value(16.73, 1), "16.7")
        self.assertEqual(format_value(None), "--")
        self.assertEqual(format_value(100, 0), "100")

    def test_clock(self):
        self.assertEqual(
            clock_text({"device": {"now_local": "2026-11-10T09:30:00+08:00"}}),
            "09:30",
        )
        self.assertEqual(clock_text({}), "--:--")


if __name__ == "__main__":
    unittest.main()
