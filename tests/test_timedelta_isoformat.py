"""Test coverage for :py:module:`timedelta_isoformat`"""
from typing import Union
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
    ("PT131211.10", timedelta(hours=13, minutes=12, seconds=11, microseconds=100000)),
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
    ("PT23:59:59.9", timedelta(hours=23, minutes=59, seconds=59.9)),
    # matching datetime.timedelta day-to-microsecond carry precision
    ("P0.000001D", timedelta(microseconds=86400)),
    ("P0.00000000001D", timedelta(microseconds=1)),
]

invalid_durations = [
    # incomplete strings
    ("", "durations must begin with the character 'P'"),
    ("T", "durations must begin with the character 'P'"),
    ("P", "no measurements found"),
    ("PT", "no measurements found"),
    ("PPT", "unexpected character 'P'"),
    ("PTT", "unexpected character 'T'"),
    ("PTP", "unexpected character 'P'"),
    # incomplete measurements
    ("P0YD", "unable to parse '' as a positive decimal"),
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
    ("PT0.0.0S", "unable to parse '0.0.0' as a positive decimal"),
    ("P1.,0D", "unable to parse '1.,0' as a positive decimal"),
    # date-format durations exceeding calendar limits
    ("P0000-367", "days value of 367 exceeds range [0..366]"),
    ("P0000-400", "days value of 400 exceeds range [0..366]"),
    ("P0000-13-00", "months value of 13 exceeds range [0..12]"),
    ("PT12:60:00", "minutes value of 60 exceeds range [0..60)"),
    ("PT12:61:00", "minutes value of 61 exceeds range [0..60)"),
    ("PT15:25:60", "seconds value of 60 exceeds range [0..60)"),
    ("PT24:00:00", "hours value of 24 exceeds range [0..24)"),
    # invalid date-format style durations
    ("P0000-1-0", "unable to parse '1-0' as a positive decimal"),
    ("PT1:2:3", "unable to parse '1:2:3' into time components"),
    ("PT01:0203", "unable to parse '01:0203' into time components"),
    ("PT01", "unable to parse '01' into time components"),
    ("PT01:02:3.4", "unable to parse '01:02:3.4' into time components"),
    ("P0000y00m00", "unable to parse '0000y00m00' into date components"),
    # decimals must have a non-empty integer value before the separator
    ("PT.5S", "unable to parse '.5' as a positive decimal"),
    ("P1M.1D", "unable to parse '.1' as a positive decimal"),
    ("PT.5:00:00", ""),
    ("PT5.:00:00", ""),
    ("PT12:34:56e10", ""),
    ("P0000-0.0", ""),
    # segment repetition
    ("PT5MT5S", "unexpected character 'T'"),
    ("P1W2W", "unexpected character 'W'"),
    # segments out-of-order
    ("P1DT5S2W", "unexpected character 'W'"),
    ("P1W1D", "unexpected character 'D'"),
    # unexpected characters within date/time components
    ("PT01:-2:03", "unable to parse '-2' as a positive decimal"),
    ("P000000.1", "unable to parse '.1' as a positive decimal"),
    ("PT000000--", "unable to parse '000000--' into time components"),
    ("PT00:00:00,-", "unable to parse '00:00:00,-' into time components"),
    # negative designator-separated values
    ("P-1DT0S", "unexpected character '-'"),
    ("P0M-2D", "unexpected character '-'"),
    ("P0DT1M-3S", "unexpected character '-'"),
]

# ambiguous cases
_ = [
    # mixed segment formats
    ("P0000-00-01T5S", "date segment format differs from time segment"),
    ("P1DT00:00:00", "date segment format differs from time segment"),
]

format_expectations = [
    (timedelta(seconds=1, microseconds=500), "PT1.0005S"),
    (timedelta(seconds=10, microseconds=0), "PT10S"),
    (timedelta(minutes=10), "PT10M"),
    (timedelta(seconds=5400), "PT1H30M"),
    (timedelta(hours=20, minutes=5), "PT20H5M"),
    (timedelta(days=1.5, minutes=4000), "P4DT6H40M"),
]


class TimedeltaISOFormat(unittest.TestCase):
    """Functional testing for :class:`timedelta_isoformat.timedelta`"""

    def test_fromisoformat_valid(self) -> None:
        """Parsing cases that should all succeed"""
        for duration_string, expected_timedelta in valid_durations:
            with self.subTest(duration_string=duration_string):
                parsed_timedelta = timedelta.fromisoformat(duration_string)
                self.assertEqual(parsed_timedelta, expected_timedelta)

    def test_fromisoformat_invalid(self) -> None:
        """Parsing cases that should all fail"""
        for duration_string, expected_reason in invalid_durations:
            with self.subTest(duration_string=duration_string):
                with self.assertRaises(ValueError) as context:
                    timedelta.fromisoformat(duration_string)
                self.assertIn(expected_reason, str(context.exception))

    def test_roundtrip_valid(self) -> None:
        """Round-trip from valid duration to string and back maintains the same value"""
        for _, valid_timedelta in valid_durations:
            with self.subTest(valid_timedelta=valid_timedelta):
                duration_string = valid_timedelta.isoformat()
                parsed_timedelta = timedelta.fromisoformat(duration_string)
                self.assertEqual(parsed_timedelta, valid_timedelta)

    class YearMonthTimedelta(timedelta):
        """Subclass of :py:class:`timedelta_isoformat.timedelta` for year/month tests"""

        def __new__(
            cls,
            *args: Union[float, int],
            months: Union[float, int],
            years: Union[float, int],
            **kwargs: Union[float, int],
        ) -> "TimedeltaISOFormat.YearMonthTimedelta":
            attribs = dict(
                __repr__=cls.__repr__,
                isoformat=cls.isoformat,
                months=months,
                years=years,
            )
            typ = type(str(cls), (timedelta,), attribs)
            return typ(*args, **kwargs)  # type: ignore

        def __repr__(self) -> str:
            fields = {
                "years": getattr(self, "years", 0),
                "months": getattr(self, "months", 0),
                "days": self.days,
                "seconds": self.seconds,
                "microseconds": self.microseconds,
            }
            arguments = ", ".join(f"{k}={v}" for k, v in fields.items() if v)
            return f"YearMonthTimedelta({arguments})"

        def isoformat(self) -> str:
            duration = timedelta.isoformat(self).lstrip("P")
            years_and_months = "P"
            years_and_months += f"{self.years}Y" if self.years else ""  # type: ignore
            years_and_months += f"{self.months}M" if self.months else ""  # type: ignore
            return f"{years_and_months}{duration}"

    @unittest.skip("not currently supported")
    def test_year_month_formatting(self) -> None:
        """Formatting of timedelta objects with year-or-month attributes"""
        year_month_timedelta = self.YearMonthTimedelta(hours=4, months=6, years=1)
        self.assertEqual("P1Y6MT4H", year_month_timedelta.isoformat())
        self.assertEqual(
            "YearMonthTimedelta(years=1, months=6, seconds=14400)",
            repr(year_month_timedelta),
        )

    def test_year_month_support_handling(self) -> None:
        """Parsing of duration strings containing zero-value year-or-month components"""
        with self.assertRaises(TypeError):
            timedelta.fromisoformat("P1Y0D")

    def test_minimal_precision(self) -> None:
        """Ensure that the smallest py3.9 datetime.timedelta is formatted correctly"""
        microsecond = timedelta.fromisoformat("PT0.000001S")
        self.assertEqual("PT0.000001S", microsecond.isoformat())

    def test_formatting_precision(self) -> None:
        """Formatting for decimal fields"""
        for sample_timedelta, expected_format in format_expectations:
            with self.subTest(sample_timedelta=sample_timedelta):
                self.assertEqual(expected_format, sample_timedelta.isoformat())
