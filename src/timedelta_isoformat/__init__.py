"""Supplemental ISO8601 duration format support for :py:class:`datetime.timedelta`"""
import datetime
from typing import Iterable, Tuple, TypeAlias

_DECIMAL_POINTS = frozenset(",.")


class timedelta(datetime.timedelta):
    """Subclass of :py:class:`datetime.timedelta` with additional methods to implement
    ISO8601-style parsing and formatting.
    """

    Components: TypeAlias = Iterable[Tuple[str, str, int | None]]
    Measurements: TypeAlias = Iterable[Tuple[str, float]]

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
        date_context = iter((("Y", "years"), ("M", "months"), ("D", "days")))
        time_context = iter((("H", "hours"), ("M", "minutes"), ("S", "seconds")))
        week_context = iter((("W", "weeks"),))

        context, value, unit = date_context, "", None
        for char in duration:
            if char.isdigit():
                value += char
                continue

            if char in _DECIMAL_POINTS:
                assert value.isdigit(), f"unexpected character '{char}'"
                value += "."
                continue

            if char == "T":
                assert context is not time_context, f"unexpected character '{char}'"
                assert context is not week_context, "cannot mix weeks with other units"
                assert not value, f"missing unit designator after '{value}'"
                context = time_context
                continue

            if char == "W":
                context = week_context
                pass

            assert not (context is week_context and unit), "cannot mix weeks with other units"
            for delimiter, unit in context:
                if char == delimiter:
                    yield value, unit, None
                    value = ""
                    break
            else:
                raise ValueError(f"unexpected character '{char}'")

        assert unit, "no measurements found"

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
                quantity = float(value)
            except (AssertionError, IndexError, ValueError) as exc:
                msg = f"unable to parse '{value}' as a positive decimal"
                raise ValueError(msg) from exc
            if not quantity:
                continue
            if limit and not (0 <= quantity <= limit if inclusive_limit else 0 <= quantity < limit):
                bounds = f"[0..{limit}" + ("]" if inclusive_limit else ")")
                raise ValueError(f"{unit} value of {value} exceeds range {bounds}")
            yield unit, quantity

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
