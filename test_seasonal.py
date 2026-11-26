import unittest
from datetime import date
from unittest.mock import patch
import companion


class SeasonalTests(unittest.TestCase):
    def test_christmas_season_and_saved_config_compatibility(self):
        for day, expected in ((date(2026, 11, 25), False),
                              (date(2026, 11, 26), True),
                              (date(2026, 12, 31), True),
                              (date(2027, 1, 1), False)):
            self.assertEqual(companion.christmas_enabled({}, day), expected)
        self.assertFalse(companion.christmas_enabled(
            {"seasonal": {"christmas": "off"}}, date(2026, 12, 10)))
        self.assertTrue(companion.christmas_enabled(
            {"seasonal": {"christmas": "on"}}, date(2026, 7, 10)))

    def test_christmas_countdown_calendar_boundaries(self):
        self.assertEqual(companion.christmas_countdown(date(2026, 11, 26))["text"], "29 DAYS")
        self.assertEqual(companion.christmas_countdown(date(2026, 12, 24))["text"], "1 DAY")
        self.assertEqual(companion.christmas_countdown(date(2026, 12, 25)),
                         {"text": "MERRY", "label": "CHRISTMAS!"})
        self.assertEqual(companion.christmas_countdown(date(2026, 12, 26)),
                         {"text": "HOLIDAY", "label": "CHEER!"})
        self.assertEqual(companion.christmas_countdown(date(2027, 1, 1))["text"], "358 DAYS")
        self.assertEqual(companion.christmas_countdown(date(2028, 2, 28))["text"], "301 DAYS")

    def test_christmas_rotation_and_priority(self):
        with patch("companion.christmas_enabled", return_value=True):
            self.assertEqual([companion.seasonal_cameo({}, i) for i in range(7)],
                             ["christmas_cozy", None, None, "christmas_countdown",
                              None, None, "christmas_cozy"])
        with patch("companion.christmas_enabled", return_value=False), \
             patch("companion.halloween_enabled", return_value=False), \
             patch("companion.autumn_enabled", return_value=True):
            self.assertEqual(companion.seasonal_cameo({}, 0), "autumn_cozy")

    def test_christmas_countdown_transport_uses_pc_calendar(self):
        runtime = companion.Runtime(music_playing=True)
        runtime.set_state("christmas_countdown", "test", "manual")
        with patch("companion.christmas_countdown",
                   return_value={"text": "1 DAY", "label": "UNTIL CHRISTMAS"}):
            fields = runtime.wire_frame().strip().split("|")
            self.assertEqual(runtime.snapshot()["seasonal"]["christmas_countdown"]["text"], "1 DAY")
        self.assertEqual(len(fields), 15)
        self.assertEqual(fields[3], "christmas_countdown")
        self.assertEqual(fields[6], "0")
        self.assertEqual(fields[10], "1 DAY")
        self.assertEqual(fields[12], "UNTIL CHRISTMAS")

    def test_autumn_auto_only_in_november_and_override(self):
        for month in range(1, 13):
            self.assertEqual(companion.autumn_enabled({}, date(2026, month, 2)), month == 11)
        self.assertFalse(companion.autumn_enabled({'seasonal': {'autumn': 'off'}}, date(2026, 11, 2)))
        self.assertTrue(companion.autumn_enabled({'seasonal': {'autumn': 'on'}}, date(2026, 12, 2)))

    def test_auto_only_in_october_and_override(self):
        for month in range(1, 13):
            self.assertEqual(companion.halloween_enabled({}, date(2026, month, 2)), month == 10)
        self.assertFalse(companion.halloween_enabled({'seasonal': {'halloween': 'off'}}, date(2026, 10, 2)))
        self.assertTrue(companion.halloween_enabled({'seasonal': {'halloween': 'on'}}, date(2026, 12, 2)))

    def test_countdown_rolls_to_next_year(self):
        self.assertEqual(companion.halloween_days(date(2026, 10, 2)), 29)
        self.assertEqual(companion.halloween_days(date(2026, 10, 31)), 0)
        self.assertEqual(companion.halloween_days(date(2026, 11, 1)), 364)

    def test_countdown_uses_existing_transport_field(self):
        runtime = companion.Runtime()
        runtime.set_state('halloween_countdown', 'test', 'manual')
        with patch('companion.halloween_days', return_value=29):
            frame = runtime.wire_frame().strip().split('|')
        self.assertEqual(len(frame), 15)
        self.assertEqual(frame[3], 'halloween_countdown')
        self.assertEqual(frame[10], '29 DAYS')
        with patch('companion.halloween_days', return_value=0):
            self.assertEqual(runtime.wire_frame().strip().split('|')[10], 'HALLOWEEN!')
