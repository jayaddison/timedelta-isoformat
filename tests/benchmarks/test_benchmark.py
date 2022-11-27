"""Benchmark tests for :py:module:`timedelta_isoformat`"""
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
    ("P0Y0DT1H20M", timedelta(hours=1, minutes=20)),
    # week durations
    ("P1W", timedelta(days=7)),
    ("P3W", timedelta(days=21)),
    # decimal measurements
    ("PT1.5S", timedelta(seconds=1, microseconds=500000)),
    ("P2DT0.5H", timedelta(days=2, minutes=30)),
    ("PT0,01S", timedelta(seconds=0.01)),
    ("PT01:01:01.01", timedelta(hours=1, minutes=1, seconds=1, microseconds=10000)),
    # date-format durations
    ("P0000000", timedelta()),
    ("P0000000T000000", timedelta()),
    ("P0000360", timedelta(days=360)),
    ("P00000004", timedelta(days=4)),
    ("P0000-00-05", timedelta(days=5)),
    ("P0000-00-00T01:02:03", timedelta(hours=1, minutes=2, seconds=3)),
    ("PT040506", timedelta(hours=4, minutes=5, seconds=6)),
    ("PT04:05:06", timedelta(hours=4, minutes=5, seconds=6)),
    # calendar edge cases
    ("P0000-366", timedelta(days=366)),
    ("PT23:59:59", timedelta(hours=23, minutes=59, seconds=59)),
]


class TimedeltaISOFormatBenchmark(unittest.TestCase):
    """Benchmark testing for :class:`timedelta_isoformat.timedelta`"""

    def test_fromisoformat_benchmark(self):
        """Benchmark the fromisoformat parser method"""
        for duration_string, _ in valid_durations * 5000:
            timedelta.fromisoformat(duration_string)

    def test_isoformat_benchmark(self):
        """Benchmark the isoformat formatting method"""
        for _, valid_timedelta in valid_durations * 1000:
            valid_timedelta.isoformat()
