"""Supplemental ISO8601 duration format support for :py:class:`datetime.timedelta`"""
from collections import defaultdict
import datetime
from string import digits

_FIELD_CHARACTERS = frozenset(digits + "-:")
_DECIMAL_CHARACTERS = frozenset(",.")

_CARRY = {
    "weeks": 7 * 24 * 60 * 60,
    "days": 24 * 60 * 60,
    "hours": 60 * 60,
    "minutes": 60,
    "seconds": 1000000,
}


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
            yield date_string[0:4], "years", None
            yield date_string[5:8], "days", 366

        # YYYY-MM-DD
        elif date_length == 10 and delimiters == [4, 7]:
            yield date_string[0:4], "years", None
            yield date_string[5:7], "months", 12
            yield date_string[8:10], "days", 31

        # YYYYDDD
        elif date_length == 7 and delimiters == []:
            yield date_string[0:4], "years", None
            yield date_string[4:7], "days", 366

        # YYYYMMDD
        elif date_length == 8 and delimiters == []:
            yield date_string[0:4], "years", None
            yield date_string[4:6], "months", 12
            yield date_string[6:8], "days", 31

        else:
            raise ValueError(f"unable to parse '{date_string}' into date components")

    @staticmethod
    def _fromtimestring(time_string):
        delimiters = [i for i, c in enumerate(time_string[0:15]) if c == ":"]
        decimal = time_string[6:7] if delimiters == [] else time_string[8:9]

        # HH:MM:SS[.ssssss]
        if delimiters == [2, 5]:
            yield time_string[0:2], "hours", 24
            yield time_string[3:5], "minutes", 60
            yield time_string[6:8], "seconds", 60
            if not decimal:
                return
            assert decimal in _DECIMAL_CHARACTERS, f"unexpected character '{decimal}'"
            yield time_string[9:15].ljust(6, "0"), "microseconds", 999999

        # HHMMSS[.ssssss]
        elif delimiters == []:
            yield time_string[0:2], "hours", 24
            yield time_string[2:4], "minutes", 60
            yield time_string[4:6], "seconds", 60
            if not decimal:
                return
            assert decimal in _DECIMAL_CHARACTERS, f"unexpected character '{decimal}'"
            yield time_string[7:13].ljust(6, "0"), "microseconds", 999999

        else:
            raise ValueError(f"unable to parse '{time_string}' into time components")

    @staticmethod
    def _carry(amount, unit, value):
        if not amount.rstrip("0."):
            return
        assert unit in _CARRY, f"unable to handle fractional {unit} value '{value}'"
        carry_unit, carry_value = (
            "microseconds" if unit == "seconds" else "seconds",
            f"{float(amount) * _CARRY[unit]:.6f}",
        )
        carry_integer, carry_remainder = carry_value[:-7], carry_value[-7:]
        yield carry_integer, carry_unit, None
        yield from timedelta._carry(carry_remainder, carry_unit, carry_value)

    @staticmethod
    def _fromdurationstring(duration):
        date_tokens = iter(("Y", "years", "M", "months", "D", "days"))
        time_tokens = iter(("H", "hours", "M", "minutes", "S", "seconds"))
        week_tokens = iter(("W", "weeks"))

        tokens, value, decimal, tail = None, "", None, None
        for char in duration:
            if char in _FIELD_CHARACTERS:
                value += char
                continue

            if char in _DECIMAL_CHARACTERS and decimal is None:
                decimal = len(value)
                value += "."
                continue

            if char == "P" and not tokens:
                tokens = date_tokens
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

            unit, integer_part, decimal_part = (
                next(tokens, None),
                value[:decimal],
                value[decimal:] if decimal is not None else "",
            )

            if decimal_part:
                yield from timedelta._carry(decimal_part, unit, value)

            if integer_part:
                yield integer_part, unit, None
            else:
                raise ValueError(f"incomplete measurement before character '{char}'")

            value, decimal = "", None

        date_tail, time_tail = (tail, value) if tokens is time_tokens else (value, None)
        if date_tail:
            yield from timedelta._fromdatestring(date_tail)
        if time_tail:
            yield "0", "hours", 0
            yield from timedelta._fromtimestring(time_tail)

        expected_token = next(tokens or date_tokens, None)
        assert not (expected_token == "Y" and not value), "no measurements found"
        assert not (
            next(week_tokens, None) is None
            and (next(date_tokens, None) != "Y" or next(time_tokens, None) != "H")
        ), "cannot mix weeks with other units"
        assert not (
            expected_token == "H" and not value
        ), "no measurements found in time segment"

    @staticmethod
    def _parse(duration, inclusive_range=True):
        results = defaultdict(int)
        for v, k, limit in timedelta._fromdurationstring(duration):
            assert v.isdigit(), f"unable to parse {k} value '{v}' as a positive integer"
            v = float(v)
            bounds = f"[0..{limit or v}" + ("]" if inclusive_range else ")")
            error_msg = f"{k} value of {v} exceeds range {bounds}"
            assert v <= (limit or v) if inclusive_range else v < (limit or v), error_msg
            results[k] += v
            if k == "hours" and limit is not None:
                inclusive_range = False
        return {k: v for k, v in results.items() if v}

    @classmethod
    def fromisoformat(cls, duration):
        """Parses an input string and returns a :py:class:`timedelta` result

        :raises: `ValueError` with an explanatory message when parsing fails
        """

        def _parse_error(reason):
            return ValueError(f"could not parse duration '{duration}': {reason}")

        try:
            measurements = cls._parse(duration)
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

        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
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
