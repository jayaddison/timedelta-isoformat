"""Supplemental ISO8601 duration format support for :py:class:`datetime.timedelta`"""
import datetime
from string import digits

_FIELD_CHARACTERS = frozenset(digits + ",-.:")


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
    def _filter(components, inclusive_range=True):
        for value, unit, limit in components:
            bounds = f"[0..{limit}" + ("]" if inclusive_range else ")")
            error_msg = f"{unit} value of {value} exceeds range {bounds}"
            assert value.isdigit(), f"expected a positive integer {unit} component"
            assert value < limit or inclusive_range, error_msg
            assert value <= limit, error_msg
            yield unit, int(value)

    @staticmethod
    def _fromdatestring(date_string):
        separator_positions = [i for i, c in enumerate(date_string[0:10]) if c == "-"]
        date_length = len(date_string)

        # YYYY-DDD
        if date_length == 8 and separator_positions == [4]:
            yield date_string[0:4], "years", "a"
            yield date_string[5:8], "days", "366"

        # YYYY-MM-DD
        elif date_length == 10 and separator_positions == [4, 7]:
            yield date_string[0:4], "years", "a"
            yield date_string[5:7], "months", "12"
            yield date_string[8:10], "days", "31"

        # YYYYDDD
        elif date_length == 7 and separator_positions == []:
            yield date_string[0:4], "years", "a"
            yield date_string[4:7], "days", "366"

        # YYYYMMDD
        elif date_length == 8 and separator_positions == []:
            yield date_string[0:4], "years", "a"
            yield date_string[4:6], "months", "12"
            yield date_string[6:8], "days", "31"

        else:
            raise ValueError(f"unable to parse '{date_string}' into date components")

    @staticmethod
    def _fromtimestring(time_string):
        separator_positions = [i for i, c in enumerate(time_string[0:15]) if c == ":"]
        time_length = len(time_string)

        # HH:MM:SS[.ssssss]
        if time_length >= 8 and separator_positions == [2, 5]:
            yield time_string[0:2], "hours", "24"
            yield time_string[3:5], "minutes", "60"
            yield time_string[6:8], "seconds", "60"
            if time_length == 8:
                return
            assert time_string[8] == ".", f"unexpected character '{time_string[8]}'"
            yield time_string[9:15].ljust(6, "0"), "microseconds", "a"

        # HHMMSS[.ssssss]
        elif time_length >= 6 and separator_positions == []:
            yield time_string[0:2], "hours", "24"
            yield time_string[2:4], "minutes", "60"
            yield time_string[4:6], "seconds", "60"
            if time_length == 6:
                return
            assert time_string[6] == ".", f"unexpected character '{time_string[6]}'"
            yield time_string[7:13].ljust(6, "0"), "microseconds", "a"

        else:
            raise ValueError(f"unable to parse '{time_string}' into time components")

    @classmethod
    def _parse(cls, duration):
        date_tokens = iter(("Y", "years", "M", "months", "D", "days"))
        time_tokens = iter(("H", "hours", "M", "minutes", "S", "seconds"))
        week_tokens = iter(("W", "weeks"))

        tokens, value, tail, measurements = None, "", None, {}
        for char in duration:
            if char in _FIELD_CHARACTERS:
                value += char
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

            assert value, f"missing measurement before character '{char}'"
            assert value[0].isdigit(), f"value '{value}' does not start with a digit"

            try:
                measurements[next(tokens)] = float(value.replace(",", "."))
            except ValueError as exc:
                raise ValueError(f"unable to parse '{value}' as a number") from exc
            value = ""

        date_tail, time_tail = (tail, value) if tokens is time_tokens else (value, None)
        if date_tail:
            components = timedelta._fromdatestring(date_tail)
            measurements |= timedelta._filter(components)
        if time_tail:
            components = timedelta._fromtimestring(time_tail)
            measurements |= timedelta._filter(components, inclusive_range=False)

        assert measurements, "no measurements found"
        assert not (
            "weeks" in measurements and len(measurements) > 1
        ), "cannot mix weeks with other units"
        assert not (
            tokens is time_tokens
            and "hours" not in measurements
            and "minutes" not in measurements
            and "seconds" not in measurements
        ), "no measurements found in time segment"

        return {k: v for k, v in measurements.items() if v}

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
            raise _parse_error(exc) from None
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
