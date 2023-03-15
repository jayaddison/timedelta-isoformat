"""Supplemental ISO8601 duration format support for :py:class:`datetime.timedelta`"""
import datetime
from enum import StrEnum
from typing import Iterable, Tuple, TypeAlias
from dataclasses import dataclass

_DECIMAL_CHARACTERS = frozenset("0123456789" + ",.")


class DateUnit(StrEnum):
    years = "Y"
    months = "M"
    days = "D"


class TimeUnit(StrEnum):
    hours = "H"
    minutes = "M"
    seconds = "S"


class WeekUnit(StrEnum):
    weeks = "W"


RawValue: TypeAlias = str
Unit: TypeAlias = DateUnit | TimeUnit | WeekUnit
MeasurementLimit: TypeAlias = int | None
MeasuredValue: TypeAlias = float

Components: TypeAlias = Iterable[Tuple[RawValue, Unit, MeasurementLimit]]
Measurements: TypeAlias = Iterable[Tuple[Unit, MeasuredValue]]


class timedelta(datetime.timedelta):
    """Subclass of :py:class:`datetime.timedelta` with additional methods to implement
    ISO8601-style parsing and formatting.
    """

    def __repr__(self) -> str:
        return f"timedelta_isoformat.{super().__repr__()}"

    @staticmethod
    def _from_date(segment: str) -> Components:
        match tuple(segment):
            # YYYY-DDD
            case _, _, _, _, "-", _, _, _:
                yield segment[0:4], DateUnit.years, None
                yield segment[5:8], DateUnit.days, 366
            # YYYY-MM-DD
            case _, _, _, _, "-", _, _, "-", _, _:
                yield segment[0:4], DateUnit.years, None
                yield segment[5:7], DateUnit.months, 12
                yield segment[8:10], DateUnit.days, 31
            # YYYYDDD
            case _, _, _, _, _, _, _:
                yield segment[0:4], DateUnit.years, None
                yield segment[4:7], DateUnit.days, 366
            # YYYYMMDD
            case _, _, _, _, _, _, _, _:
                yield segment[0:4], DateUnit.years, None
                yield segment[4:6], DateUnit.months, 12
                yield segment[6:8], DateUnit.days, 31
            case _:
                raise ValueError(f"unable to parse '{segment}' into date components")

    @staticmethod
    def _from_time(segment: str) -> Components:
        match tuple(segment):
            # HH:MM:SS[.ssssss]
            case _, _, ":", _, _, ":", _, _, ".", *_:
                yield segment[0:2], TimeUnit.hours, 24
                yield segment[3:5], TimeUnit.minutes, 60
                yield segment[6:15], TimeUnit.seconds, 60
            # HH:MM:SS
            case _, _, ":", _, _, ":", _, _:
                yield segment[0:2], TimeUnit.hours, 24
                yield segment[3:5], TimeUnit.minutes, 60
                yield segment[6:8], TimeUnit.seconds, 60
            # HHMMSS[.ssssss]
            case _, _, _, _, _, _, ".", *_:
                yield segment[0:2], TimeUnit.hours, 24
                yield segment[2:4], TimeUnit.minutes, 60
                yield segment[4:13], TimeUnit.seconds, 60
            # HHMMSS
            case _, _, _, _, _, _:
                yield segment[0:2], TimeUnit.hours, 24
                yield segment[2:4], TimeUnit.minutes, 60
                yield segment[4:6], TimeUnit.seconds, 60
            case _:
                raise ValueError(f"unable to parse '{segment}' into time components")

    @staticmethod
    def _from_designators(duration: str) -> Components:
        """Parser for designator-separated ISO-8601 duration strings

        The code sweeps through the input exactly once, expecting to find measurements
        in order of largest-to-smallest unit from left-to-right (with the exception of
        week measurements, which must be the only measurement in the string if present).
        """
        context, remaining_tokens, value = DateUnit, iter(DateUnit), ""
        weeks_visited, values_found = False, 0
        for char in duration:
            if char in _DECIMAL_CHARACTERS:
                value += char
                continue

            if char == "T" and context is not TimeUnit:
                assert not value, f"expected a unit designator after '{value}'"
                context, remaining_tokens, value = TimeUnit, iter(TimeUnit), ""
                continue

            if char == "W" and context is DateUnit:
                context, remaining_tokens = WeekUnit, iter(WeekUnit)
                weeks_visited = True
                pass

            if char not in remaining_tokens:
                raise ValueError(f"unexpected character '{char}'")

            yield value, context(char), None
            value = ""
            values_found += 1

        assert values_found, "no measurements found"
        assert not weeks_visited or values_found == 1, "cannot mix weeks with other units"

    @classmethod
    def _from_duration(cls, duration: str) -> Measurements:
        """Selects and runs an appropriate parser for ISO-8601 duration strings

        The format of these strings is composed of two segments; date measurements
        are situated between the 'P' and 'T' characters, and time measurements are
        situated between the 'T' character and the end-of-string.

        If no unit designator is found at the end of the duration string, then
        an attempt is made to parse the segment as a fixed-length date or time.
        """
        assert duration.startswith("P"), "durations must begin with the character 'P'"

        if duration[-1].isupper():
            components = cls._from_designators(duration[1:])
            yield from cls._to_measurements(components, inclusive_limit=True)
            return

        date_segment, _, time_segment = duration[1:].partition("T")
        if date_segment:
            components = cls._from_date(date_segment)
            yield from cls._to_measurements(components, inclusive_limit=True)
        if time_segment:
            components = cls._from_time(time_segment)
            yield from cls._to_measurements(components, inclusive_limit=False)

    @staticmethod
    def _to_measurements(components: Components, inclusive_limit: bool) -> Measurements:
        for value, unit, limit in components:
            try:
                assert value[0].isdigit()
                quantity = float("+" + value.replace(",", "."))
            except (AssertionError, IndexError, ValueError) as exc:
                msg = f"unable to parse '{value}' as a positive decimal"
                raise ValueError(msg) from exc
            if quantity:
                yield unit.name, quantity
            if limit and (quantity > limit if inclusive_limit else quantity >= limit):
                bounds = f"[0..{limit}" + ("]" if inclusive_limit else ")")
                raise ValueError(f"{unit.name} value of {value} exceeds range {bounds}")

    @classmethod
    def fromisoformat(cls, duration: str) -> "timedelta":
        """Parses an input string and returns a :py:class:`timedelta` result

        :raises: `ValueError` with an explanatory message when parsing fails
        """
        try:
            return cls(**dict(cls._from_duration(duration)))
        except (AssertionError, ValueError) as exc:
            raise ValueError(f"could not parse duration '{duration}': {exc}") from exc

    def isoformat(self) -> str:
        """Produce an ISO8601-style representation of this :py:class:`timedelta`"""
        if not self:
            return "P0D"

        minutes, seconds = divmod(self.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if self.microseconds:
            seconds += self.microseconds / 1_000_000  # type: ignore

        result = f"P{self.days}D" if self.days else "P"
        if hours or minutes or seconds:
            result += "T"
            result += f"{hours}H" if hours else ""
            result += f"{minutes}M" if minutes else ""
            result += f"{seconds:.6f}".rstrip("0").rstrip(".") + "S" if seconds else ""
        return result
