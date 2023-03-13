"""Supplemental ISO8601 duration format support for :py:class:`datetime.timedelta`"""
import datetime
from enum import StrEnum
from typing import Iterable, Tuple, TypeAlias
from dataclasses import dataclass

_DECIMAL_CHARACTERS = frozenset("0123456789" + ",.")

RawValue: TypeAlias = str
Unit: TypeAlias = str
MeasurementLimit: TypeAlias = int | None
MeasuredValue: TypeAlias = float

Components: TypeAlias = Iterable[Tuple[RawValue, Unit, MeasurementLimit]]
Measurements: TypeAlias = Iterable[Tuple[Unit, MeasuredValue]]

class DateContext(StrEnum):
    YEARS = "Y"
    MONTHS = "M"
    DAYS = "D"

class TimeContext(StrEnum):
    HOURS = "H"
    MINUTES = "M"
    SECONDS = "S"

class WeekContext(StrEnum):
    WEEKS = "W"


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
                yield segment[0:4], "years", None
                yield segment[5:8], "days", 366
            # YYYY-MM-DD
            case _, _, _, _, "-", _, _, "-", _, _:
                yield segment[0:4], "years", None
                yield segment[5:7], "months", 12
                yield segment[8:10], "days", 31
            # YYYYDDD
            case _, _, _, _, _, _, _:
                yield segment[0:4], "years", None
                yield segment[4:7], "days", 366
            # YYYYMMDD
            case _, _, _, _, _, _, _, _:
                yield segment[0:4], "years", None
                yield segment[4:6], "months", 12
                yield segment[6:8], "days", 31
            case _:
                raise ValueError(f"unable to parse '{segment}' into date components")

    @staticmethod
    def _from_time(segment: str) -> Components:
        match tuple(segment):
            # HH:MM:SS[.ssssss]
            case _, _, ":", _, _, ":", _, _, ".", *_:
                yield segment[0:2], "hours", 24
                yield segment[3:5], "minutes", 60
                yield segment[6:15], "seconds", 60
            # HH:MM:SS
            case _, _, ":", _, _, ":", _, _:
                yield segment[0:2], "hours", 24
                yield segment[3:5], "minutes", 60
                yield segment[6:8], "seconds", 60
            # HHMMSS[.ssssss]
            case _, _, _, _, _, _, ".", *_:
                yield segment[0:2], "hours", 24
                yield segment[2:4], "minutes", 60
                yield segment[4:13], "seconds", 60
            # HHMMSS
            case _, _, _, _, _, _:
                yield segment[0:2], "hours", 24
                yield segment[2:4], "minutes", 60
                yield segment[4:6], "seconds", 60
            case _:
                raise ValueError(f"unable to parse '{segment}' into time components")

    @staticmethod
    def _from_designators(duration: str) -> Components:
        """Parser for designator-separated ISO-8601 duration strings

        The code sweeps through the input exactly once, expecting to find measurements
        in order of largest-to-smallest unit from left-to-right (with the exception of
        week measurements, which must be the only measurement in the string if present).
        """
        date_context = iter(DateContext)
        time_context = iter(TimeContext)
        week_context = iter(WeekContext)

        contexts_encountered, context, value = set(), date_context, ""
        for char in duration:
            if char in _DECIMAL_CHARACTERS:
                value += char
                continue

            if char == "T" and context is not time_context:
                assert not value, f"expected a unit designator after '{value}'"
                context, value = time_context, ""
                continue

            if char == "W" and context is date_context:
                context = week_context
                pass

            try:
                while (unit := next(context)) != char: continue
            except StopIteration:
                raise ValueError(f"unexpected character '{char}'")

            contexts_encountered.add(type(unit))
            yield value, unit.name.lower(), None
            value = ""

        assert contexts_encountered, "no measurements found"
        assert WeekContext not in contexts_encountered or len(contexts_encountered) == 1, "cannot mix weeks with other units"

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
                yield unit, quantity
            if limit and (quantity > limit if inclusive_limit else quantity >= limit):
                bounds = f"[0..{limit}" + ("]" if inclusive_limit else ")")
                raise ValueError(f"{unit} value of {value} exceeds range {bounds}")

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
