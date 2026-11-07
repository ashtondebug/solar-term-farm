import unittest

import _bootstrap  # noqa: F401
from fakes.hardware import FakeI2C
from sensors.sht31 import SHT31, crc8, decode


class SHT31Tests(unittest.TestCase):
    def test_crc8_known_vector(self):
        self.assertEqual(crc8(b"\xbe\xef"), 0x92)

    def test_decode_midscale(self):
        temperature, humidity = decode(0x6666, 0x8000)
        self.assertAlmostEqual(temperature, 25.0, places=1)
        self.assertAlmostEqual(humidity, 50.0, places=1)

    def test_read_valid_frame(self):
        raw_temp = 0x6666
        raw_humidity = 0x8000
        data = bytes(
            [
                raw_temp >> 8,
                raw_temp & 0xFF,
                crc8(bytes([raw_temp >> 8, raw_temp & 0xFF])),
                raw_humidity >> 8,
                raw_humidity & 0xFF,
                crc8(bytes([raw_humidity >> 8, raw_humidity & 0xFF])),
            ]
        )
        sensor = SHT31(FakeI2C([data]), sleep=lambda _seconds: None)
        temperature, humidity = sensor.read(100)
        self.assertTrue(temperature.valid)
        self.assertTrue(humidity.valid)
        self.assertAlmostEqual(temperature.value, 25.0, places=1)
        self.assertAlmostEqual(humidity.value, 50.0, places=1)

    def test_crc_failure(self):
        data = bytes([0x66, 0x66, 0x00, 0x80, 0x00, 0x00])
        sensor = SHT31(FakeI2C([data]), sleep=lambda _seconds: None)
        temperature, humidity = sensor.read(100)
        self.assertFalse(temperature.valid)
        self.assertEqual(temperature.error, "crc_error")
        self.assertFalse(humidity.valid)
        self.assertEqual(humidity.error, "crc_error")


if __name__ == "__main__":
    unittest.main()
