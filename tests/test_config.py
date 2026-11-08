import unittest

import _bootstrap  # noqa: F401
from config import default_config, deep_merge, public_config, validate_config


class ConfigTests(unittest.TestCase):
    def test_defaults_are_valid(self):
        self.assertEqual(validate_config(default_config()), [])

    def test_range_validation(self):
        config = default_config()
        config["irrigation"]["max_run_s"] = 999
        errors = validate_config(config)
        self.assertTrue(any("max_run_s" in item for item in errors))

    def test_calibration_pair_must_be_complete(self):
        config = default_config()
        config["calibration"]["soil_dry"] = 50000
        errors = validate_config(config)
        self.assertTrue(any("soil_wet" in item for item in errors))

    def test_calibration_span(self):
        config = default_config()
        config["calibration"]["soil_dry"] = 50000
        config["calibration"]["soil_wet"] = 49900
        errors = validate_config(config)
        self.assertTrue(any("too close" in item for item in errors))

    def test_public_config_removes_pin(self):
        config = default_config()
        config["security"]["pin"] = "123456"
        public = public_config(config)
        self.assertNotIn("pin", public["security"])
        self.assertTrue(public["security"]["pin_required"] is False)

    def test_deep_merge(self):
        merged = deep_merge({"a": {"b": 1, "c": 2}}, {"a": {"b": 9}})
        self.assertEqual(merged["a"]["b"], 9)
        self.assertEqual(merged["a"]["c"], 2)

    def test_plant_stage_and_weights(self):
        config = default_config()
        config["plant"].update(
            {"profile": "tomato", "stage": "flowering", "weights": {"soil": 0.5, "temp": 0.2, "humidity": 0.2, "light": 0.1}}
        )
        self.assertEqual(validate_config(config), [])
        config["plant"]["stage"] = "unknown"
        self.assertTrue(any("plant.stage" in item for item in validate_config(config)))
        config["plant"].update({"stage": "growth", "weights": {"soil": 0.5}})
        errors = validate_config(config)
        self.assertTrue(any("plant.weights.temp" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
