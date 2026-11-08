import unittest

import _bootstrap  # noqa: F401
from sensors.base import Reading
from suitability.model import evaluate
from suitability.plants import get_profile


def readings(soil=60, temp=24, humidity=65, light=15000, ts=1000):
    return {
        "soil": Reading(soil, "%", True, ts),
        "air_temp": Reading(temp, "C", True, ts),
        "air_humidity": Reading(humidity, "%", True, ts),
        "light": Reading(light, "lx", True, ts),
    }


class SuitabilityTests(unittest.TestCase):
    def test_all_optimal(self):
        result = evaluate(readings(), get_profile("general"), now=1000)
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["status"], "good")

    def test_severe_metric_is_capped(self):
        result = evaluate(readings(temp=5), get_profile("general"), now=1000)
        self.assertIsNotNone(result["score"])
        self.assertLessEqual(result["score"], 45)

    def test_invalid_data_has_no_score(self):
        data = readings()
        data["soil"] = Reading(None, "%", False, 1000, "uncalibrated")
        result = evaluate(data, get_profile("general"), now=1000)
        self.assertIsNone(result["score"])
        self.assertEqual(result["status"], "unavailable")
        self.assertTrue(result["reasons"])

    def test_stale_data_has_no_score(self):
        result = evaluate(readings(ts=100), get_profile("general"), now=1000, stale_s=90)
        self.assertIsNone(result["score"])
        self.assertTrue(any("stale" in reason for reason in result["reasons"]))

    def test_stage_changes_weights(self):
        growth = get_profile("tomato", "growth")
        flowering = get_profile("tomato", "flowering")
        self.assertEqual(flowering["stage_name"], "开花结果期")
        self.assertAlmostEqual(sum(flowering["weights"].values()), 1.0)
        self.assertNotEqual(growth["weights"], flowering["weights"])
        result = evaluate(readings(), flowering, now=1000)
        self.assertEqual(result["profile"], "tomato")
        self.assertEqual(result["stage"], "flowering")
        self.assertEqual(result["profile_name"], "番茄")

    def test_custom_weights_override_profile(self):
        profile = get_profile(
            "general",
            "growth",
            {"soil": 1.0, "temp": 0.0, "humidity": 0.0, "light": 0.0},
        )
        self.assertEqual(profile["weights"]["soil"], 1.0)
        self.assertEqual(profile["weights"]["temp"], 0.0)
        result = evaluate(readings(soil=50, temp=5), profile, now=1000)
        self.assertEqual(result["components"]["soil"], 100)
        self.assertNotIn("temp: missing", result["reasons"])


if __name__ == "__main__":
    unittest.main()
