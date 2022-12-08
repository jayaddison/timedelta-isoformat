"""Algebraic test coverage for :py:module:`timedelta_isoformat`"""
import unittest

from timedelta_isoformat import timedelta


magnitude_expectations = [
    ({"days": 1, "hours": -1}, timedelta(hours=23)),
    ({"weeks": 3, "days": -2}, timedelta(days=19)),
    ({"hours": -2, "days": -2}, timedelta(hours=50)),
    ({"hours": 24, "days": -1}, timedelta()),
    ({"hours": -12, "minutes": 780}, timedelta(hours=1)),
]

summation_expectations = [
    (timedelta(hours=2), timedelta(hours=-2), timedelta()),
    (timedelta(hours=4), timedelta(hours=-2), timedelta(hours=2)),
]

subtraction_expectations = [
    (timedelta(days=5), timedelta(hours=24), timedelta(days=4)),
    (timedelta(seconds=-1), timedelta(seconds=-1), timedelta(seconds=0)),
]

negation_timedeltas = [
    timedelta(days=1, hours=1, seconds=1),
    timedelta(days=5, seconds=-2),
    timedelta(days=-5, seconds=2),
]


class TimedeltaAlgebra(unittest.TestCase):
    """Instance creation testing for :class:`timedelta_isoformat.timedelta`"""

    def test_instance_magnitude(self) -> None:
        """Verify the duration length of constructed timedeltas"""
        for kwargs, expected_timedelta in magnitude_expectations:
            with self.subTest(constructor_arguments=kwargs):
                constructed_timedelta = abs(timedelta(**kwargs))
                self.assertEqual(constructed_timedelta, expected_timedelta)

    def test_instance_summation(self) -> None:
        """Check the results of addition of duration pairs"""
        for a, b, result in summation_expectations:
            with self.subTest(a=a, b=b):
                self.assertEqual(a + b, result)

    def test_instance_subtraction(self) -> None:
        """Check the results of subtraction of duration pairs"""
        for a, b, result in subtraction_expectations:
            with self.subTest(a=a, b=b):
                self.assertEqual(a - b, result)

    def test_instance_negation(self) -> None:
        """Check the results of subtraction of duration pairs"""
        for t in negation_timedeltas:
            with self.subTest(t=t):
                self.assertEqual(t, -(-t))
