"""Supplemental ISO8601 duration format support for :py:class:`datetime.timedelta`"""
import datetime
from string import digits

_FIELD_CHARACTERS = frozenset(digits + ",.-:")
_DECIMAL_SIGNS = frozenset(",.")


class timedelta(datetime.timedelta):
    """Subclass of :py:class:`datetime.timedelta` with additional methods to implement
    ISO8601-style parsing and formatting.
    """

    def __repr__(self):
        fields = {
            "years": getattr(self, "years", 0),
            "months": getattr(self, "months", 0),
            "days": self.days,
            "seconds": self.seconds,
            "microseconds": self.microseconds,
        }
        arguments = ", ".join(f"{k}={v}" for k, v in fields.items() if v)
        return f"timedelta_isoformat.timedelta({arguments})"

    def __str__(self):
        return self.isoformat()

    @staticmethod
    def _fromdatestring(date_string):
        delimiters = [i for i, c in enumerate(date_string[0:10]) if c == "-"]
        date_length = len(date_string)

        # YYYY-DDD
        if date_length == 8 and delimiters == [4]:
            yield date_string[0:4], "years", None, True
            yield date_string[5:8], "days", 366, True

        # YYYY-MM-DD
        elif date_length == 10 and delimiters == [4, 7]:
            yield date_string[0:4], "years", None, True
            yield date_string[5:7], "months", 12, True
            yield date_string[8:10], "days", 31, True

        # YYYYDDD
        elif date_length == 7 and delimiters == []:
            yield date_string[0:4], "years", None, True
            yield date_string[4:7], "days", 366, True

        # YYYYMMDD
        elif date_length == 8 and delimiters == []:
            yield date_string[0:4], "years", None, True
            yield date_string[4:6], "months", 12, True
            yield date_string[6:8], "days", 31, True

        else:
            raise ValueError(f"unable to parse '{date_string}' into date components")

    @staticmethod
    def _fromtimestring(time_string):
        delimiters = [i for i, c in enumerate(time_string[0:15]) if c == ":"]
        decimal = time_string[6:7] if delimiters == [] else time_string[8:9]
        if decimal and decimal not in _DECIMAL_SIGNS:
            raise ValueError(f"unexpected character '{decimal}'")

        # HH:MM:SS[.ssssss]
        if delimiters == [2, 5]:
            yield time_string[0:2], "hours", 24, True
            yield time_string[3:5], "minutes", 60, True
            yield time_string[6:15], "seconds", 60, False

        # HHMMSS[.ssssss]
        elif delimiters == []:
            yield time_string[0:2], "hours", 24, True
            yield time_string[2:4], "minutes", 60, True
            yield time_string[4:13], "seconds", 60, False

        else:
            raise ValueError(f"unable to parse '{time_string}' into time components")

    @staticmethod
    def _fromdurationstring(duration):
        """Parsing code for designator-separated ISO-8601 strings, like 'PT1H30M'

        The format of these strings is composed of two segments; date measurements
        are situated between the 'P' and 'T' characters, and time measurements are
        situated between the 'T' character and the end-of-string.

        The code sweeps through the input exactly once, expecting to find measurements
        in order of largest to smallest unit from left-to-right (with the exception of
        week measurements, which must be the only measurement in the string if present).

        If no unit designator has been found when we reach the end of a segment, then
        an attempt is made to parse the segment as a fixed-length date or time.
        """
        date_tokens = iter(("Y", "years", "M", "months", "D", "days"))
        time_tokens = iter(("H", "hours", "M", "minutes", "S", "seconds"))
        week_tokens = iter(("W", "weeks"))

        assert duration.startswith("P"), "durations must begin with the character 'P'"
        assert not duration.endswith("T"), "no measurements found in time segment"

        tokens, value, tail = date_tokens, "", None
        for char in duration[1:]:
            if char in _FIELD_CHARACTERS:
                value += char
                continue

            if char == "T" and tokens is not time_tokens:
                value, tail, tokens = "", value, time_tokens
                continue

            if char == "W" and tokens is date_tokens:
                tokens = week_tokens
                pass

            # Note: this advances and may exhaust the token iterator
            if char not in tokens:
                raise ValueError(f"unexpected character '{char}'")

            yield value, next(tokens, None), None, False
            value = ""

        date_tail, time_tail = (tail, value) if tokens is time_tokens else (value, None)
        if date_tail:
            yield from timedelta._fromdatestring(date_tail)
        if time_tail:
            yield "0", "hours", 0, False
            yield from timedelta._fromtimestring(time_tail)
        if date_tail or time_tail:
            return

        weeks_parsed = next(week_tokens, None) != "W"
        time_parsed = next(time_tokens, None) != "H" or next(date_tokens, None) != "Y"
        assert weeks_parsed or time_parsed, "no measurements found"
        assert weeks_parsed != time_parsed, "cannot mix weeks with other units"

    @staticmethod
    def _to_measurements(components, inclusive_range=True):
        for value, unit, limit, integer_only in components:
            try:
                assert value.isdigit() if integer_only else value[0].isdigit()
                quantity = float("+" + value.replace(",", "."))
            except (AssertionError, IndexError, ValueError):
                raise ValueError(f"unable to parse '{value}' as a positive number")
            if limit and quantity >= limit + inclusive_range:
                bounds = f"[0..{limit}" + ("]" if inclusive_range else ")")
                raise ValueError(f"{unit} value of {value} exceeds range {bounds}")
            if quantity:
                yield unit, quantity
            if unit == "hours" and limit is not None:
                inclusive_range = False

    @classmethod
    def fromisoformat(cls, duration):
        """Parses an input string and returns a :py:class:`timedelta` result

        :raises: `ValueError` with an explanatory message when parsing fails
        """

        def _parse_error(reason):
            return ValueError(f"could not parse duration '{duration}': {reason}")

        try:
            measurements = dict(cls._to_measurements(cls._fromdurationstring(duration)))
            return cls(**measurements)
        except (AssertionError, ValueError) as exc:
            raise _parse_error(exc) from exc
        except TypeError as exc:
            if measurements.get("years") or measurements.get("months"):
                raise _parse_error("year and month fields are not supported") from exc
            raise exc

    def isoformat(self):
        """Produce an ISO8601-style representation of this :py:class:`timedelta`"""
        if not self:
            return "P0D"

        years = getattr(self, "years", 0)
        months = getattr(self, "months", 0)
        days = self.days
        seconds = self.seconds

        minutes, seconds = int(seconds / 60), self.seconds % 60
        hours, minutes = int(minutes / 60), minutes % 60
        if self.microseconds:
            seconds += self.microseconds / 10 ** 6

        result = "P"
        result += f"{years}Y" if years else ""
        result += f"{months}M" if months else ""
        result += f"{days}D" if days else ""
        result += "T" if hours or minutes or seconds else ""
        result += f"{hours}H" if hours else ""
        result += f"{minutes}M" if minutes else ""
        result += f"{seconds:.6f}".rstrip("0").rstrip(".") + "S" if seconds else ""
        return result
