import unittest

import _bootstrap  # noqa: F401
from fakes.hardware import FakeADC
from sensors.soil import SoilSensor, percent_from_raw, validate_calibration


class SoilTests(unittest.TestCase):
    def test_normal_conversion(self):
        percent, error = percent_from_raw(45000, 60000, 30000)
        self.assertIsNone(error)
        self.assertAlmostEqual(percent, 50.0)

    def test_reversed_endpoints(self):
        percent, error = percent_from_raw(45000, 30000, 60000)
        self.assertIsNone(error)
        self.assertAlmostEqual(percent, 50.0)

    def test_clamping(self):
        self.assertEqual(percent_from_raw(1000, 60000, 30000)[0], 100.0)
        self.assertEqual(percent_from_raw(65000, 60000, 30000)[0], 0.0)

    def test_invalid_span(self):
        self.assertEqual(percent_from_raw(1000, 50000, 49900)[1], "calibration_span_too_small")

    def test_uncalibrated(self):
        self.assertEqual(percent_from_raw(1000, None, None)[1], "uncalibrated")
        self.assertEqual(validate_calibration(None, None), "uncalibrated")

    def test_sensor_read(self):
        sensor = SoilSensor(FakeADC(45000), lambda: {"soil_dry": 60000, "soil_wet": 30000}, None)
        reading = sensor.read(100)
        self.assertTrue(reading.valid)
        self.assertAlmostEqual(reading.value, 50.0)

    def test_sensor_uncalibrated_is_invalid(self):
        sensor = SoilSensor(FakeADC(45000), lambda: {"soil_dry": None, "soil_wet": None}, None)
        reading = sensor.read(100)
        self.assertFalse(reading.valid)
        self.assertEqual(reading.error, "uncalibrated")


if __name__ == "__main__":
    unittest.main()
