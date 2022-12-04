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


class TimedeltaAlgebra(unittest.TestCase):
    """Instance creation testing for :class:`timedelta_isoformat.timedelta`"""

    def test_instance_magnitude(self):
        """Verify the duration length of constructed timedeltas"""
        for kwargs, expected_timedelta in magnitude_expectations:
            with self.subTest(constructor_arguments=kwargs):
                constructed_timedelta = abs(timedelta(**kwargs))
                self.assertEqual(constructed_timedelta, expected_timedelta)
