"""Supplemental ISO8601 duration format support for :py:class:`datetime.timedelta`"""
from dataclasses import dataclass
import datetime
from typing import Iterable, Tuple, TypeAlias

_NUMBER_FORMAT = frozenset("0123456789,.")


class timedelta(datetime.timedelta):
    """Subclass of :py:class:`datetime.timedelta` with additional methods to implement
    ISO8601-style parsing and formatting.
    """

    @dataclass
    class Component:
        value: str
        unit: str
        limit: int | None = None
        quantity: float = 0

        def __post_init__(self) -> None:
            assert self.value[0:1].isdigit(), f"unable to parse '{self.value}' as a positive decimal"
            self.quantity = float(self.value)
            try:
                assert self._bounds_check()
            except AssertionError as exc:
                raise ValueError(f"{self.unit} value of {self.value} exceeds range {exc}")

        def _bounds_check(self) -> bool:
            if self.limit is None:
                assert 0 <= self.quantity, "[0..+∞)"
            elif self.limit in (24, 60):
                assert 0 <= self.quantity < self.limit, f"[0..{self.limit})"
            else:
                assert 0 <= self.quantity <= self.limit, f"[0..{self.limit}]"
            return True

    Components: TypeAlias = Iterable[Component]

    def __repr__(self) -> str:
        return f"timedelta_isoformat.{super().__repr__()}"

    @classmethod
    def _parse_date(cls, segment: str) -> Components:
        match tuple(segment):

            # YYYY-DDD
            case _, _, _, _, "-", _, _, _:
                yield cls.Component(segment[0:4], "years")
                yield cls.Component(segment[5:8], "days", 366)

            # YYYY-MM-DD
            case _, _, _, _, "-", _, _, "-", _, _:
                yield cls.Component(segment[0:4], "years")
                yield cls.Component(segment[5:7], "months", 12)
                yield cls.Component(segment[8:10], "days", 31)

            # YYYYDDD
            case _, _, _, _, _, _, _:
                yield cls.Component(segment[0:4], "years")
                yield cls.Component(segment[4:7], "days", 366)

            # YYYYMMDD
            case _, _, _, _, _, _, _, _:
                yield cls.Component(segment[0:4], "years")
                yield cls.Component(segment[4:6], "months", 12)
                yield cls.Component(segment[6:8], "days", 31)

            case _:
                raise ValueError(f"unable to parse '{segment}' into date components")

    @classmethod
    def _parse_time(cls, segment: str) -> Components:
        match tuple(segment):

            # HH:MM:SS[.ssssss]
            case _, _, ":", _, _, ":", _, _, ".", *_:
                yield cls.Component(segment[0:2], "hours", 24)
                yield cls.Component(segment[3:5], "minutes", 60)
                yield cls.Component(segment[6:15], "seconds", 60)

            # HH:MM:SS
            case _, _, ":", _, _, ":", _, _:
                yield cls.Component(segment[0:2], "hours", 24)
                yield cls.Component(segment[3:5], "minutes", 60)
                yield cls.Component(segment[6:8], "seconds", 60)

            # HHMMSS[.ssssss]
            case _, _, _, _, _, _, ".", *_:
                yield cls.Component(segment[0:2], "hours", 24)
                yield cls.Component(segment[2:4], "minutes", 60)
                yield cls.Component(segment[4:13], "seconds", 60)

            # HHMMSS
            case _, _, _, _, _, _:
                yield cls.Component(segment[0:2], "hours", 24)
                yield cls.Component(segment[2:4], "minutes", 60)
                yield cls.Component(segment[4:6], "seconds", 60)

            case _:
                raise ValueError(f"unable to parse '{segment}' into time components")

    @classmethod
    def _parse_designators(cls, duration: str) -> Components:
        """Parser for designator-separated ISO-8601 duration strings

        The code sweeps through the input exactly once, expecting to find measurements
        in order of largest-to-smallest unit from left-to-right (with the exception of
        week measurements, which must be the only measurement in the string if present).
        """
        date_context = iter((("Y", "years"), ("M", "months"), ("D", "days")))
        time_context = iter((("H", "hours"), ("M", "minutes"), ("S", "seconds")))
        week_context = iter((("W", "weeks"),))

        context, value, unit = date_context, "", None
        for char in duration:
            if char in _NUMBER_FORMAT:
                value += char if char.isdigit() else "."
                continue

            if char == "T" and context is date_context:
                assert not value, f"missing unit designator after '{value}'"
                context = time_context
                continue

            if char == "W":
                context = week_context
                pass

            assert not (context is week_context and unit), "cannot mix weeks with other units"
            for delimiter, unit in context:
                if char == delimiter:
                    yield cls.Component(value, unit)
                    value = ""
                    break
            else:
                raise ValueError(f"unexpected character '{char}'")

        assert unit, "no measurements found"

    @classmethod
    def _parse_duration(cls, duration: str) -> Components:
        """Selects and runs an appropriate parser for ISO-8601 duration strings

        The format of these strings is composed of two segments; date measurements
        are situated between the 'P' and 'T' characters, and time measurements are
        situated between the 'T' character and the end-of-string.

        If no unit designator is found at the end of the duration string, then
        an attempt is made to parse the segment as a fixed-length date or time.
        """
        assert duration.startswith("P"), "durations must begin with the character 'P'"

        if duration[-1].isupper():
            yield from cls._parse_designators(duration[1:])
            return

        date_segment, _, time_segment = duration[1:].partition("T")
        if date_segment:
            yield from cls._parse_date(date_segment)
        if time_segment:
            yield from cls._parse_time(time_segment)

    @classmethod
    def fromisoformat(cls, duration: str) -> "timedelta":
        """Parses an input string and returns a :py:class:`timedelta` result

        :raises: `ValueError` with an explanatory message when parsing fails
        """
        try:
            return cls(**{m.unit: m.quantity for m in cls._parse_duration(duration) if m.quantity})
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
