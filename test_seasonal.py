import unittest
from datetime import date
from unittest.mock import patch
import companion


class SeasonalTests(unittest.TestCase):
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
        self.assertEqual(len(frame), 14)
        self.assertEqual(frame[3], 'halloween_countdown')
        self.assertEqual(frame[10], '29 DAYS')
        with patch('companion.halloween_days', return_value=0):
            self.assertEqual(runtime.wire_frame().strip().split('|')[10], 'HALLOWEEN!')
