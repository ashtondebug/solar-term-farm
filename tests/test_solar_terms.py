import unittest
from datetime import datetime, timezone

import _bootstrap  # noqa: F401
from solar_terms.astronomy import (
    all_payloads,
    current_term,
    solar_apparent_longitude,
    term_index,
    term_start_ts,
)


def epoch(year, month, day, hour=0, minute=0):
    return int(datetime(year, month, day, hour, minute, tzinfo=timezone.utc).timestamp())


class SolarTermTests(unittest.TestCase):
    def test_lichun_2024(self):
        now = epoch(2024, 2, 4, 12, 0)
        term = current_term(now)
        self.assertEqual(term["name"], "立春")
        known = epoch(2024, 2, 4, 8, 26)
        self.assertLess(abs(term_start_ts(now) - known), 3 * 3600)

    def test_chunfen_2024(self):
        now = epoch(2024, 3, 20, 12, 0)
        term = current_term(now)
        self.assertEqual(term["name"], "春分")
        self.assertLess(abs(term["longitude"]), 1.0)

    def test_dongzhi_2024(self):
        now = epoch(2024, 12, 21, 12, 0)
        self.assertEqual(current_term(now)["name"], "冬至")

    def test_index_wraps_to_dahan(self):
        now = epoch(2024, 1, 25, 12, 0)
        self.assertEqual(term_index(now), 23)
        self.assertEqual(current_term(now)["name"], "大寒")

    def test_apparent_longitude_range(self):
        for month in (1, 4, 7, 10):
            value = solar_apparent_longitude(epoch(2024, month, 15))
            self.assertGreaterEqual(value, 0.0)
            self.assertLess(value, 360.0)

    def test_all_payloads(self):
        payload = all_payloads(epoch(2024, 6, 1))
        self.assertEqual(len(payload), 24)
        self.assertEqual(sum(1 for item in payload if item["is_current"]), 1)

    def test_all_terms_have_farming_tips(self):
        from solar_terms.data import TERMS
        from solar_terms.culture import CULTURE

        self.assertEqual(len(TERMS), 24)
        self.assertEqual(len(CULTURE), 24)
        for term in TERMS:
            content = CULTURE[term["name"]]
            self.assertTrue(term["available"], term["name"])
            self.assertGreaterEqual(len(content["tips"]), 3, term["name"])
            self.assertGreaterEqual(len(content["proverbs"]), 3, term["name"])
            self.assertGreaterEqual(len(content["customs"]), 3, term["name"])
            for title, detail in content["tips"]:
                self.assertTrue(title)
                self.assertTrue(detail)


if __name__ == "__main__":
    unittest.main()
