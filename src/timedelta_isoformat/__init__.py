"""Supplemental ISO8601 duration format support for :py:class:`datetime.timedelta`"""
import datetime
from typing import Iterator, TypeAlias


class timedelta(datetime.timedelta):
    """Subclass of :py:class:`datetime.timedelta` with additional methods to implement
    ISO8601-style parsing and formatting.
    """
    __slots__ = ()

    Components: TypeAlias = Iterator[tuple[str, str, int | None, bool]]
    Measurements: TypeAlias = Iterator[tuple[str, float]]

    def __repr__(self) -> str:
        return f"timedelta_isoformat.{super().__repr__()}"

    @staticmethod
    def _parse_date(segment: str) -> Components:
        match tuple(segment):

            # YYYY-DDD
            case _, _, _, _, "-", _, _, _:
                yield segment[0:4], "years", None, True
                yield segment[5:8], "days", 366, True

            # YYYY-MM-DD
            case _, _, _, _, "-", _, _, "-", _, _:
                yield segment[0:4], "years", None, True
                yield segment[5:7], "months", 12, True
                yield segment[8:10], "days", 31, True

            # YYYYDDD
            case _, _, _, _, _, _, _:
                yield segment[0:4], "years", None, True
                yield segment[4:7], "days", 366, True

            # YYYYMMDD
            case _, _, _, _, _, _, _, _:
                yield segment[0:4], "years", None, True
                yield segment[4:6], "months", 12, True
                yield segment[6:8], "days", 31, True

            case _:
                raise ValueError(f"unable to parse '{segment}' into date components")

    @staticmethod
    def _parse_time(segment: str) -> Components:
        match tuple(segment):

            # HH:MM:SS[.ssssss]
            case _, _, ":", _, _, ":", _, _, ".", *_:
                yield segment[0:2], "hours", 24, True
                yield segment[3:5], "minutes", 60, True
                yield segment[6:15], "seconds", 60, False

            # HH:MM:SS
            case _, _, ":", _, _, ":", _, _:
                yield segment[0:2], "hours", 24, True
                yield segment[3:5], "minutes", 60, True
                yield segment[6:8], "seconds", 60, True

            # HHMMSS[.ssssss]
            case _, _, _, _, _, _, ".", *_:
                yield segment[0:2], "hours", 24, True
                yield segment[2:4], "minutes", 60, True
                yield segment[4:13], "seconds", 60, False

            # HHMMSS
            case _, _, _, _, _, _:
                yield segment[0:2], "hours", 24, True
                yield segment[2:4], "minutes", 60, True
                yield segment[4:6], "seconds", 60, True

            case _:
                raise ValueError(f"unable to parse '{segment}' into time components")

    @staticmethod
    def _parse(duration: Iterator[str], context: Iterator[str] | None = None) -> Components:
        """Parser for ISO-8601 duration strings

        Each string in this format is composed of either one or two segments: date
        measurements are situated between the initial 'P' and subsequent (optional) 'T'
        character, and when present, time measurements are situated between the 'T'
        character and the end of the string.

        The implementation sweeps through the input exactly once, expecting to encounter
        measurements in order of largest-to-smallest unit from left-to-right. As an
        exception, week measurement units must not be combined with any other date or
        time units. Segments that lack units are parsed as ISO8601 date/time strings.
        """
        date_context = iter(("Y", "years", "M", "months", "D", "days"))
        context = date_context if not context and next(duration, "") == "P" else context
        assert context, "durations must begin with the character 'P'"

        accumulator, unit = "", ""
        for char in duration:
            if char in ",-.0123456789:":
                accumulator += "." if char == "," else char
                continue

            elif char == "T" and context is date_context:
                time_context = iter(("H", "hours", "M", "minutes", "S", "seconds"))
                yield from timedelta._parse(duration, context=time_context)
                break

            elif char == "W" and context is date_context and not unit:
                context = iter(("W", "weeks"))
                pass

            if char not in context:
                raise ValueError(f"unexpected character '{char}'")

            value, unit, accumulator = accumulator, next(context), ""
            yield value, unit, None, False

        if accumulator:
            assert not unit, f"missing unit designator after '{accumulator}'"
            parser = timedelta._parse_date if context is date_context else timedelta._parse_time
            yield from parser(accumulator)

    @staticmethod
    def _to_measurements(components: Components) -> Measurements:
        unit = None
        for value, unit, limit, integer_only in components:
            assert value.isdigit() if integer_only else value[0:1].isdigit(), f"unable to parse '{value}' as a positive number"
            quantity = float(value)
            if limit is None:
                assert 0 <= quantity, f"{unit} value of {value} exceeds range [0..+∞)"
            elif limit in (24, 60):
                assert 0 <= quantity < limit, f"{unit} value of {value} exceeds range [0..{limit})"
            else:
                assert 0 <= quantity <= limit, f"{unit} value of {value} exceeds range [0..{limit}]"
            if quantity:
                yield unit, quantity
        assert unit, "no measurements found"

    @staticmethod
    def fromisoformat(duration: str) -> "timedelta":
        """Parses an input string and returns a :py:class:`timedelta` result

        :raises: `ValueError` with an explanatory message when parsing fails
        """
        assert isinstance(duration, str), "expected duration to be a str"
        try:
            return timedelta(**dict(timedelta._to_measurements(timedelta._parse(iter(duration)))))
        except (AssertionError, ValueError) as exc:
            raise ValueError(f"could not parse duration '{duration}': {exc}") from exc

    def isoformat(self) -> str:
        """Produce an ISO8601-style representation of this :py:class:`timedelta`"""
        assert self >= timedelta(0), f"cannot produce ISO format for negative {self!r}"
        if not self:
            return "P0D"

        if self.days % 7 == 0 and not self.seconds and not self.microseconds:
            return f"P{int(self.days / 7)}W"

        days = self.days
        minutes, seconds = divmod(self.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if self.microseconds:
            seconds += self.microseconds / 1_000_000  # type: ignore

        if hours and days:
            hours += days * 24
            days %= 1
        if minutes and hours:
            minutes += hours * 60
            hours %= 1
        if seconds and minutes:
            seconds += minutes * 60
            minutes %= 1

        result = f"P{days}D" if days else "P"
        if hours or minutes or seconds:
            result += "T"
            result += f"{hours}H" if hours else ""
            result += f"{minutes}M" if minutes else ""
            result += f"{seconds:.6f}".rstrip("0").rstrip(".") + "S" if seconds else ""
        return result
