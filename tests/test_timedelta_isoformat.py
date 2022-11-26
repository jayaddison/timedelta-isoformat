import unittest

from timedelta_isoformat import timedelta


valid_durations = [
    # empty duration
    ("P0D", timedelta()),
    ("PT0S", timedelta()),
    # designator-format durations
    ("P3D", timedelta(days=3)),
    ("P3DT1H", timedelta(days=3, hours=1)),
    ("P0DT1H20M", timedelta(hours=1, minutes=20)),
    # week durations
    ("P1W", timedelta(days=7)),
    ("P3W", timedelta(days=21)),
    # decimal measurements
    ("PT1.5S", timedelta(seconds=1, microseconds=500000)),
    ("P2DT0.5H", timedelta(days=2, minutes=30)),
    ("PT0,01S", timedelta(seconds=0.01)),
]

invalid_durations = [
    # incomplete strings
    ("", "durations must begin with the character 'P'"),
    ("P", "no measurements found"),
    # missing measurements
    ("P0YD", "missing measurement before character 'D'"),
    # repeated designators
    ("P1DT1H3H1M", "unexpected character 'H'"),
    ("P1D3D", "unexpected character 'D'"),
    # incorrectly-ordered designators
    ("PT5S1M", "unexpected character 'M'"),
    ("P0DT5M1H", "unexpected character 'H'"),
    # invalid units within segment
    ("PT1DS", "unexpected character 'D'"),
    ("P1HT0S", "unexpected character 'H'"),
    # mixing week units with other units
    ("P1WT1H", "cannot mix weeks with other units"),
    # incorrect quantities
    ("PT0.0.0S", "unable to intepret '0.0.0' as a numeric value"),
    ("P1.,0D", "unable to intepret '1.,0' as a numeric value"),
]


class TimedeltaISOFormat(unittest.TestCase):
    def test_fromisoformat_valid(self):
        for duration_string, expected_timedelta in valid_durations:
            with self.subTest(duration_string=duration_string):
                parsed_timedelta = timedelta.fromisoformat(duration_string)
                self.assertEqual(parsed_timedelta, expected_timedelta)

    def test_fromisoformat_invalid(self):
        for duration_string, expected_reason in invalid_durations:
            with self.subTest(duration_string=duration_string):
                with self.assertRaises(TypeError) as context:
                    timedelta.fromisoformat(duration_string)
                self.assertIn(expected_reason, str(context.exception))

    def test_roundtrip_valid(self):
        for _, valid_timedelta in valid_durations:
            with self.subTest(valid_timedelta=valid_timedelta):
                duration_string = valid_timedelta.isoformat()
                parsed_timedelta = timedelta.fromisoformat(duration_string)
                self.assertEqual(parsed_timedelta, valid_timedelta)
