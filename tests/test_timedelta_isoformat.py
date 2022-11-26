import unittest

from timedelta_isoformat import timedelta


valid_durations = [
    # empty duration
    ("P0D", timedelta()),
    ("PT0S", timedelta()),
]

invalid_durations = [
    # incomplete strings
    (""),
    ("P"),
]


class TimedeltaISOFormat(unittest.TestCase):
    def test_fromisoformat_valid(self):
        for duration_string, expected_timedelta in valid_durations:
            with self.subTest(duration_string=duration_string):
                parsed_timedelta = timedelta.fromisoformat(duration_string)
                self.assertEqual(parsed_timedelta, expected_timedelta)

    def test_fromisoformat_invalid(self):
        for duration_string in invalid_durations:
            with self.subTest(duration_string=duration_string):
                with self.assertRaises(TypeError):
                    timedelta.fromisoformat(duration_string)

    def test_roundtrip_valid(self):
        for _, valid_timedelta in valid_durations:
            with self.subTest(valid_timedelta=valid_timedelta):
                duration_string = valid_timedelta.isoformat()
                parsed_timedelta = timedelta.fromisoformat(duration_string)
                self.assertEqual(parsed_timedelta, valid_timedelta)
