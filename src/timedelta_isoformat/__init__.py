"""Supplemental ISO8601 duration format support for :py:class:`datetime.timedelta`"""
import datetime
from typing import Iterable, TypeAlias


class timedelta(datetime.timedelta):
    """Subclass of :py:class:`datetime.timedelta` with additional methods to implement
    ISO8601-style parsing and formatting.
    """
    __slots__ = ()

    Components: TypeAlias = Iterable[tuple[str, str, int | None, bool]]
    Measurements: TypeAlias = Iterable[tuple[str, float]]

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
    def _parse_designators(duration: str) -> Components:
        """Parser for designator-separated ISO-8601 duration strings

        The code sweeps through the input exactly once, expecting to find measurements
        in order of largest-to-smallest unit from left-to-right (with the exception of
        week measurements, which must be the only measurement in the string if present).
        """
        date_context = iter((("Y", "years"), ("M", "months"), ("D", "days")))

        context, value, unit = date_context, "", None
        for char in duration:
            if char in {",", ".", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}:
                value += char if char.isdigit() else "."
                continue

            if char == "T" and context is date_context:
                assert not value, f"missing unit designator after '{value}'"
                context = iter((("H", "hours"), ("M", "minutes"), ("S", "seconds")))
                continue

            if char == "W":
                assert not unit, "cannot mix weeks with other units"
                context = iter((("W", "weeks"),))
                pass

            for delimiter, unit in context:
                if char == delimiter:
                    yield value, unit, None, False
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
        else:
            date_segment, _, time_segment = duration[1:].partition("T")
            yield from cls._parse_date(date_segment) if date_segment else ()
            yield from cls._parse_time(time_segment) if time_segment else ()

    @staticmethod
    def _to_measurements(components: Components) -> Measurements:
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

    @classmethod
    def fromisoformat(cls, duration: str) -> "timedelta":
        """Parses an input string and returns a :py:class:`timedelta` result

        :raises: `ValueError` with an explanatory message when parsing fails
        """
        assert isinstance(duration, str), "expected duration to be a str"
        try:
            return cls(**dict(cls._to_measurements(cls._parse_duration(duration))))
        except (AssertionError, ValueError) as exc:
            raise ValueError(f"could not parse duration '{duration}': {exc}") from exc

    def isoformat(self) -> str:
        """Produce an ISO8601-style representation of this :py:class:`timedelta`"""
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
