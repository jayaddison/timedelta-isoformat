"""Test coverage for :py:module:`timedelta_isoformat`"""
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
    # date-format durations
    ("P0000000", timedelta()),
    ("P0000360", timedelta(days=360)),
    ("P00000004", timedelta(days=4)),
    ("P0000-00-05", timedelta(days=5)),
    ("P0000-00-00T01:02:03", timedelta(hours=1, minutes=2, seconds=3)),
    # calendar edge cases
    ("P0000-366", timedelta(days=366)),
]

invalid_durations = [
    # incomplete strings
    ("", "durations must begin with the character 'P'"),
    ("P", "no measurements found"),
    ("P0DT", "no measurements found in time segment"),
    ("P1DT", "no measurements found in time segment"),
    ("P0000001T", "no measurements found in time segment"),
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
    ("PT0.0.0S", "unable to parse '0.0.0' as a number"),
    ("P1.,0D", "unable to parse '1.,0' as a number"),
    # date-format durations exceeding calendar limits
    ("P0000-400", "days value of 400 exceeds range 0..366"),
    ("P0000-13-00", "months value of 13 exceeds range 0..12"),
    ("PT12:60:00", "minutes value of 60 exceeds range 0..59"),
    ("PT12:61:00", "minutes value of 61 exceeds range 0..59"),
    ("PT15:25:60", "seconds value of 60 exceeds range 0..59"),
    # invalid date-format style durations
    ("P0000-1-0", "unable to parse '0000-1-0' into date components"),
    ("PT1:2:3", "unable to parse '1:2:3' into time components"),
]


class TimedeltaISOFormat(unittest.TestCase):
    """Functional testing for :class:`timedelta_isoformat.timedelta`"""

    def test_fromisoformat_valid(self):
        """Parsing cases that should all succeed"""
        for duration_string, expected_timedelta in valid_durations:
            with self.subTest(duration_string=duration_string):
                parsed_timedelta = timedelta.fromisoformat(duration_string)
                self.assertEqual(parsed_timedelta, expected_timedelta)

    def test_fromisoformat_invalid(self):
        """Parsing cases that should all fail"""
        for duration_string, expected_reason in invalid_durations:
            with self.subTest(duration_string=duration_string):
                with self.assertRaises(ValueError) as context:
                    timedelta.fromisoformat(duration_string)
                self.assertIn(expected_reason, str(context.exception))

    def test_roundtrip_valid(self):
        """Round-trip from valid duration to string and back maintains the same value"""
        for _, valid_timedelta in valid_durations:
            with self.subTest(valid_timedelta=valid_timedelta):
                duration_string = valid_timedelta.isoformat()
                parsed_timedelta = timedelta.fromisoformat(duration_string)
                self.assertEqual(parsed_timedelta, valid_timedelta)
