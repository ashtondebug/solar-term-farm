import json
import unittest

import _bootstrap  # noqa: F401
from sensors.base import Reading
from suitability.model import evaluate
from suitability.plants import PROFILES, get_profile, normalize_import, register_profiles


def payload():
    return {
        "version": 1,
        "plants": [
            {
                "key": "test-tomato",
                "name": "测试番茄",
                "stages": {
                    "seedling": {
                        "ranges": {
                            "soil_moisture": [55, 70],
                            "air_temp": [18, 24],
                            "air_humidity": [60, 80],
                            "light": [8000, 20000],
                            "soil_temp": [16, 22],
                            "air_temp_night": [15, 20],
                            "vpd_kpa": [0.7, 1.1],
                            "dli_mol_m2_day": [8, 14],
                        },
                        "weights": {
                            "soil_moisture": 0.35,
                            "air_temp": 0.3,
                            "air_humidity": 0.15,
                            "light": 0.2,
                        },
                        "days_to_next_stage": 18,
                        "advice": ["保持基质均匀湿润，避免夜间叶面结露。"],
                    }
                },
                "traits": {
                    "lifecycle": "annual",
                    "plant_habit": "upright",
                    "root_depth_cm": 30,
                    "mature_height_cm": 150,
                    "spacing_cm": 45,
                    "support": "stake",
                    "pollination": "self",
                    "disease_risks": ["高湿环境易发灰霉病"],
                    "pest_risks": ["蚜虫"],
                    "photoperiod_type": "day_neutral",
                    "frost_tolerance_c": 0,
                    "heat_stress_c": 35,
                    "drought_sensitivity": "medium",
                    "waterlogging_sensitivity": "high",
                    "irrigation_strategy": "pulse",
                    "max_dry_down_pct": 35,
                    "source": "示例资料",
                    "confidence": "medium",
                    "reviewed": False,
                    "control_eligible": False,
                },
            }
        ],
    }


class PlantProfileTests(unittest.TestCase):
    def tearDown(self):
        PROFILES.pop("test-tomato", None)

    def test_normalize_and_stage_ranges(self):
        profiles = normalize_import(payload())
        self.assertEqual(profiles[0]["key"], "test-tomato")
        ranges = profiles[0]["stages"]["seedling"]["ranges"]
        self.assertEqual(ranges["soil"], [55.0, 70.0])
        self.assertEqual(ranges["temp"], [18.0, 24.0])
        self.assertEqual(ranges["soil_temp"], [16.0, 22.0])
        self.assertEqual(ranges["air_temp_night"], [15.0, 20.0])
        self.assertEqual(ranges["vpd_kpa"], [0.7, 1.1])
        self.assertEqual(profiles[0]["traits"]["plant_habit"], "upright")
        self.assertEqual(profiles[0]["traits"]["disease_risks"], ["高湿环境易发灰霉病"])
        self.assertEqual(profiles[0]["stages"]["seedling"]["days_to_next_stage"], 18.0)
        self.assertAlmostEqual(sum(profiles[0]["stages"]["seedling"]["weights"].values()), 1.0)
        register_profiles(profiles)
        profile = get_profile("test-tomato", "seedling")
        self.assertEqual(profile["ranges"]["soil"], [55.0, 70.0])
        self.assertEqual(profile["traits"]["pollination"], "self")
        self.assertEqual(profile["stage_info"]["days_to_next_stage"], 18.0)
        data = {
            "soil": Reading(60, "%", True, 1000),
            "air_temp": Reading(20, "C", True, 1000),
            "air_humidity": Reading(70, "%", True, 1000),
            "light": Reading(10000, "lx", True, 1000),
        }
        result = evaluate(data, profile, now=1000)
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["stage"], "seedling")
        self.assertEqual(result["traits"]["plant_habit"], "upright")
        self.assertEqual(result["stage_info"]["days_to_next_stage"], 18.0)
        self.assertEqual(result["ranges"]["soil_temp"], [16.0, 22.0])

    def test_import_rejects_builtin_key(self):
        bad = payload()
        bad["plants"][0]["key"] = "tomato"
        with self.assertRaises(ValueError):
            normalize_import(bad)

    def test_import_requires_measured_ranges(self):
        bad = payload()
        del bad["plants"][0]["stages"]["seedling"]["ranges"]["light"]
        with self.assertRaises(ValueError):
            normalize_import(bad)


if __name__ == "__main__":
    unittest.main()
