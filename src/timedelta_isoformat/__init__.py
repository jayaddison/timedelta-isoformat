"""Supplemental ISO8601 duration format support for :py:class:`datetime.timedelta`"""
import datetime
from typing import Iterable, Optional, Tuple, Type

_DIGITS, _DECIMAL_SIGNS = frozenset("0123456789"), frozenset(",.")
_FORMAT = _DIGITS | _DECIMAL_SIGNS


class timedelta(datetime.timedelta):
    """Subclass of :py:class:`datetime.timedelta` with additional methods to implement
    ISO8601-style parsing and formatting.
    """

    def __repr__(self) -> str:
        return f"timedelta_isoformat.{super().__repr__()}"

    @staticmethod
    def _from_date(segment: str) -> Iterable[Tuple[str, str, Optional[int]]]:
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
    def _from_time(segment: str) -> Iterable[Tuple[str, str, Optional[int]]]:
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
    def _from_designators(duration: str) -> Iterable[Tuple[str, str, Optional[int]]]:
        """Parser for designator-separated ISO-8601 duration strings

        The code sweeps through the input exactly once, expecting to find measurements
        in order of largest-to-smallest unit from left-to-right (with the exception of
        week measurements, which must be the only measurement in the string if present).
        """
        date_tokens = iter(("Y", "years", "M", "months", "D", "days"))
        time_tokens = iter(("H", "hours", "M", "minutes", "S", "seconds"))
        week_tokens = iter(("W", "weeks"))

        tokens, value = date_tokens, ""
        for char in duration:
            if char in _FORMAT:
                value += char
                continue

            if char == "T" and tokens is not time_tokens:
                tokens, value = time_tokens, ""
                continue

            if char == "W" and tokens is date_tokens:
                tokens = week_tokens
                pass

            # Note: this advances and may exhaust the token iterator
            if char not in tokens:
                raise ValueError(f"unexpected character '{char}'")

            yield value, next(tokens), None, False
            value = ""

        weeks_parsed = next(week_tokens, None) != "W"
        time_parsed = next(time_tokens, None) != "H" or next(date_tokens, None) != "Y"
        assert weeks_parsed or time_parsed, "no measurements found"
        assert weeks_parsed != time_parsed, "cannot mix weeks with other units"

    @staticmethod
    def _from_duration(duration: str) -> Iterable[Tuple[str, float]]:
        """Selects and runs an appropriate parser for ISO-8601 duration strings

        The format of these strings is composed of two segments; date measurements
        are situated between the 'P' and 'T' characters, and time measurements are
        situated between the 'T' character and the end-of-string.

        If no unit designator is found at the end of the duration string, then
        an attempt is made to parse the segment as a fixed-length date or time.
        """
        assert duration.startswith("P"), "durations must begin with the character 'P'"

        if duration[-1].isupper():
            components = timedelta._from_designators(duration[1:])
            yield from timedelta._to_measurements(components)
            return

        date_segment, _, time_segment = duration[1:].partition("T")
        if date_segment:
            components = timedelta._from_date(date_segment)
            yield from timedelta._to_measurements(components, inclusive_range=True)
        if time_segment:
            components = timedelta._from_time(time_segment)
            yield from timedelta._to_measurements(components, inclusive_range=False)

    @staticmethod
    def _to_measurements(
        components: Iterable[Tuple[str, str, Optional[int]]],
        inclusive_range: bool = True,
    ) -> Iterable[Tuple[str, float]]:
        for value, unit, limit, integer_only in components:
            try:
                assert value.isdigit() if integer_only else value[0].isdigit()
                quantity = float("+" + value.replace(",", "."))
            except (AssertionError, IndexError, ValueError) as exc:
                msg = f"unable to parse '{value}' as a positive number"
                raise ValueError(msg) from exc
            if not quantity:
                continue
            if limit and (quantity > limit if inclusive_range else quantity >= limit):
                bounds = f"[0..{limit}" + ("]" if inclusive_range else ")")
                raise ValueError(f"{unit} value of {value} exceeds range {bounds}")
            yield unit, quantity

    @classmethod
    def fromisoformat(cls: Type["timedelta"], duration: str) -> "timedelta":
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
