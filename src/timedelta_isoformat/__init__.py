"""Supplemental ISO8601 duration format support for :py:class:`datetime.timedelta`"""
import datetime
from string import digits

_FIELD_CHARACTERS = frozenset(digits + "-:")
_DECIMAL_CHARACTERS = frozenset(",.")


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
    def _filter(components):
        for value, unit, limit in components:
            assert value[
                :1
            ].isdigit(), f"unexpected prefix '{value[:1]}' in {unit} value '{value}'"
            value = int(value)
            limit = limit or value
            assert value <= limit, f"{unit} value of {value} exceeds range 0..{limit}"
            yield unit, value

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
        decimal_mark = time_string[6:7] if delimiters == [] else time_string[8:9]

        # HH:MM:SS[.ssssss]
        if delimiters == [2, 5]:
            yield time_string[0:2], "hours", 23
            yield time_string[3:5], "minutes", 59
            yield time_string[6:8], "seconds", 59
            if not decimal_mark:
                return
            assert (
                decimal_mark in _DECIMAL_CHARACTERS
            ), f"unexpected character '{decimal_mark}'"
            yield time_string[9:15].ljust(6, "0"), "microseconds", None

        # HHMMSS[.ssssss]
        elif delimiters == []:
            yield time_string[0:2], "hours", 23
            yield time_string[2:4], "minutes", 59
            yield time_string[4:6], "seconds", 59
            if not decimal_mark:
                return
            assert (
                decimal_mark in _DECIMAL_CHARACTERS
            ), f"unexpected character '{decimal_mark}'"
            yield time_string[7:13].ljust(6, "0"), "microseconds", None

        else:
            raise ValueError(f"unable to parse '{time_string}' into time components")

    @classmethod
    def _parse(cls, duration):
        date_tokens = iter(("Y", "years", "M", "months", "D", "days"))
        time_tokens = iter(("H", "hours", "M", "minutes", "S", "seconds"))
        week_tokens = iter(("W", "weeks"))

        tokens, value, tail, decimal_mark, measurements = None, "", 0, False, {}
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

            if char in _DECIMAL_CHARACTERS and not decimal_mark:
                decimal_mark = len(value)
                value += char
                continue

            # Note: this advances and may exhaust the token iterator
            if char not in tokens:
                raise ValueError(f"unexpected character '{char}'")

            assert value, f"missing measurement before character '{char}'"

            unit = next(tokens)
            assert value[
                :1
            ].isdigit(), f"unexpected prefix '{value[:1]}' in {unit} value '{value}'"

            measurement_type = float if decimal_mark else int
            try:
                measurements[unit] = measurement_type(value.replace(",", "."))
            except ValueError as exc:
                raise ValueError(f"unable to parse '{value}' as a number") from exc
            value, decimal_mark = "", 0

        date_tail, time_tail = (tail, value) if tokens is time_tokens else (value, None)
        if date_tail:
            measurements |= timedelta._filter(timedelta._fromdatestring(date_tail))
        if time_tail:
            measurements |= timedelta._filter(timedelta._fromtimestring(time_tail))

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
        result += f"{seconds}S" if seconds else ""
        return result
