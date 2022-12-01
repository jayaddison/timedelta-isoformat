"""Test coverage for :py:module:`timedelta_isoformat`"""
import unittest

from timedelta_isoformat import timedelta


valid_durations = [
    # empty duration
    ("P0D", timedelta()),
    ("P0Y", timedelta()),
    ("PT0S", timedelta()),
    # designator-format durations
    ("P3D", timedelta(days=3)),
    ("P3DT1H", timedelta(days=3, hours=1)),
    ("P0DT1H20M", timedelta(hours=1, minutes=20)),
    ("P0Y0DT1H20M", timedelta(hours=1, minutes=20)),
    # week durations
    ("P1W", timedelta(days=7)),
    ("P3W", timedelta(days=21)),
    # decimal measurements
    ("PT1.5S", timedelta(seconds=1, microseconds=500000)),
    ("P2DT0.5H", timedelta(days=2, minutes=30)),
    ("PT0,01S", timedelta(seconds=0.01)),
    ("PT01:01:01.01", timedelta(hours=1, minutes=1, seconds=1, microseconds=10000)),
    ("P1.5W", timedelta(days=10, hours=12)),
    ("P1.01D", timedelta(days=1, seconds=864)),
    ("P1.01DT1S", timedelta(days=1, seconds=865)),
    ("P10.0DT12H", timedelta(days=10, hours=12)),
    # date-format durations
    ("P0000000", timedelta()),
    ("P0000000T000000", timedelta()),
    ("P0000360", timedelta(days=360)),
    ("P00000004", timedelta(days=4)),
    ("P0000-00-05", timedelta(days=5)),
    ("P0000-00-00T01:02:03", timedelta(hours=1, minutes=2, seconds=3)),
    ("PT040506", timedelta(hours=4, minutes=5, seconds=6)),
    ("PT04:05:06", timedelta(hours=4, minutes=5, seconds=6)),
    ("PT00:00:00.001", timedelta(microseconds=1000)),
    # calendar edge cases
    ("P0000-366", timedelta(days=366)),
    ("PT23:59:59", timedelta(hours=23, minutes=59, seconds=59)),
    # matching datetime.timedelta day-to-microsecond carry precision
    ("P0.000001D", timedelta(microseconds=86400)),
    ("P0.00000000001D", timedelta(microseconds=1)),
]

invalid_durations = [
    # incomplete strings
    ("", "no measurements found"),
    ("P", "no measurements found"),
    ("P0DT", "no measurements found in time segment"),
    ("P1DT", "no measurements found in time segment"),
    ("P0Y5MT", "no measurements found in time segment"),
    ("P0000001T", "no measurements found in time segment"),
    # incomplete measurements
    ("P0YD", "missing measurement before character 'D'"),
    # repeated designators
    ("P1DT1H3H1M", "unexpected character 'H'"),
    ("P1D3D", "unexpected character 'D'"),
    ("P0MT1HP1D", "unexpected character 'P'"),
    # incorrectly-ordered designators
    ("PT5S1M", "unexpected character 'M'"),
    ("P0DT5M1H", "unexpected character 'H'"),
    # invalid units within segment
    ("PT1DS", "unexpected character 'D'"),
    ("P1HT0S", "unexpected character 'H'"),
    # mixing week units with other units
    ("P1WT1H", "cannot mix weeks with other units"),
    ("P0Y1W", "cannot mix weeks with other units"),
    # incorrect quantities
    ("PT0.0.0S", "unable to parse '0.0.0' as a number"),
    ("P1.,0D", "unable to parse '1.,0' as a number"),
    # date-format durations exceeding calendar limits
    ("P0000-400", "days value of 400 exceeds range 0..366"),
    ("P0000-13-00", "months value of 13 exceeds range 0..12"),
    ("PT12:60:00", "minutes value of 60 exceeds range 0..59"),
    ("PT12:61:00", "minutes value of 61 exceeds range 0..59"),
    ("PT15:25:60", "seconds value of 60 exceeds range 0..59"),
    ("PT24:00:00", "hours value of 24 exceeds range 0..23"),
    # invalid date-format style durations
    ("P0000-1-0", "unable to parse '0000-1-0' into date components"),
    ("PT1:2:3", "unable to parse '1:2:3' into time components"),
    ("PT01:0203", "unable to parse '01:0203' into time components"),
    ("PT01", "unable to parse '01' into time components"),
    # decimals must have a non-empty integer value before the separator
    ("PT.5S", "value '.5' does not start with a digit"),
    ("P1M.1D", "value '.1' does not start with a digit"),
    # segment repetition
    ("PT5MT5S", "unexpected character 'T'"),
    ("P1W2W", "unexpected character 'W'"),
    # segments out-of-order
    ("P1DT5S2W", "unexpected character 'W'"),
    ("P1W1D", "unexpected character 'D'"),
    # unexpected characters within date/time components
    ("PT01:-2:03", "expected a positive integer minutes component"),
    ("P000000.1", "expected a positive integer days component"),
    ("PT000000--", "unexpected character '-'"),
    ("PT00:00:00,-", "expected a positive integer microseconds component"),
    # negative designator-separated values
    ("P-1DT0S", "value '-1' does not start with a digit"),
    ("P0M-2D", "value '-2' does not start with a digit"),
    ("P0DT1M-3S", "value '-3' does not start with a digit"),
]

# ambiguous cases
_ = [
    # mixed segment formats
    ("P0000-00-01T5S", "date segment format differs from time segment"),
    ("P1DT00:00:00", "date segment format differs from time segment"),
    ("PT131211,10", "expected a positive integer microseconds component"),
]

format_expectations = [
    (timedelta(seconds=1, microseconds=500), "PT1.0005S"),
    (timedelta(seconds=10, microseconds=0), "PT10S"),
    (timedelta(minutes=10), "PT10M"),
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

    class YearMonthTimedelta(timedelta):
        """Subclass of :py:class:`timedelta_isoformat.timedelta` for year/month tests"""

        def __new__(cls, *args, months=0, years=0, **kwargs):
            typ = type(str(cls), (timedelta,), dict(months=months, years=years))
            return typ(*args, **kwargs)

    def test_year_month_formatting(self):
        """Formatting of timedelta objects with year-or-month attributes"""
        year_month_timedelta = self.YearMonthTimedelta(years=1, months=6, hours=4)
        self.assertEqual("P1Y6MT4H", year_month_timedelta.isoformat())
        self.assertEqual("P1Y6MT4H", str(year_month_timedelta))
        self.assertEqual(
            "timedelta_isoformat.timedelta(years=1, months=6, seconds=14400)",
            repr(year_month_timedelta),
        )

    class YearMonthUnsupportedTimedelta(timedelta):
        """Subclass of :py:class:`timedelta_isoformat.timedelta` for exception tests"""

        def __new__(cls, *args, **kwargs):
            if "years" in kwargs or "months" in kwargs:
                raise TypeError
            # days, seconds, microseconds, milliseconds, minutes, hours, weeks
            if len(args) > 7:
                raise TypeError
            return super(*args)

    def test_year_month_support_handling(self):
        """Parsing of duration strings containing zero-value year-or-month components"""
        with self.assertRaises(ValueError) as raised:
            self.YearMonthUnsupportedTimedelta.fromisoformat("P1Y0D")
        self.assertIn("year and month fields are not supported", str(raised.exception))

    def test_minimal_precision(self):
        """Ensure that the smallest py3.9 datetime.timedelta is formatted correctly"""
        microsecond = timedelta.fromisoformat("PT0.000001S")
        self.assertEqual("PT0.000001S", microsecond.isoformat())

    def test_formatting_precision(self):
        """Formatting for decimal fields"""
        for sample_timedelta, expected_format in format_expectations:
            with self.subTest(sample_timedelta=sample_timedelta):
                self.assertEqual(expected_format, sample_timedelta.isoformat())
