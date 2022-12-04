"""Supplemental ISO8601 duration format support for :py:class:`datetime.timedelta`"""
import datetime
from string import digits

_FIELD_CHARACTERS = frozenset(digits + ",-.:")


class timedelta(datetime.timedelta):
    """Subclass of :py:class:`datetime.timedelta` with additional methods to implement
    ISO8601-style parsing and formatting.
    """

    @staticmethod
    def _filter(components, inclusive_range=True):
        for quantity, unit, limit in components:
            if not quantity.isdigit():
                raise ValueError(f"expected a positive integer within {unit} component")
            if quantity > limit if inclusive_range else quantity >= limit:
                bounds = f"[0..{limit}" + ("]" if inclusive_range else ")")
                raise ValueError(f"{unit} value of {quantity} exceeds range {bounds}")
            yield unit, float(quantity)

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
            if time_string[8] != ".":
                raise ValueError(f"unexpected character '{time_string[8]}'")
            yield time_string[9:15].ljust(6, "0"), "microseconds", "a"

        # HHMMSS[.ssssss]
        elif time_length >= 6 and separator_positions == []:
            yield time_string[0:2], "hours", "24"
            yield time_string[2:4], "minutes", "60"
            yield time_string[4:6], "seconds", "60"
            if time_length == 6:
                return
            if time_string[6] != ".":
                raise ValueError(f"unexpected character '{time_string[6]}'")
            yield time_string[7:13].ljust(6, "0"), "microseconds", "a"

        else:
            raise ValueError(f"unable to parse '{time_string}' into time components")

    @classmethod
    def fromisoformat(cls, duration_string):
        """Parses an input string and returns a :py:class:`timedelta` result

        :raises: `ValueError` with an explanatory message when parsing fails
        """

        def _parse_error(reason):
            return ValueError(f"could not parse duration '{duration_string}': {reason}")

        input_stream = iter(duration_string)
        if next(input_stream, None) != "P":
            raise _parse_error("durations must begin with the character 'P'")

        date = iter(("Y", "years", "M", "months", "D", "days"))
        time = iter(("H", "hours", "M", "minutes", "S", "seconds"))
        week = iter(("W", "weeks"))

        stream, value, tail, measurements = date, "", None, {}
        while char := next(input_stream, None):
            if char in _FIELD_CHARACTERS:
                value += char
                continue

            if char == "T" and stream is not time:
                value, tail, stream = "", value, time
                continue

            if char == "W" and stream is date:
                stream = week
                pass

            # Note: this advances and may exhaust the iterator
            if char not in stream:
                raise _parse_error(f"unexpected character '{char}'")

            if not value:
                raise _parse_error(f"missing measurement before character '{char}'")

            if not value[0].isdigit():
                raise _parse_error(f"value '{value}' does not start with a digit")

            try:
                measurements[next(stream)] = float(value.replace(",", "."))
            except ValueError as exc:
                raise _parse_error(f"unable to parse '{value}' as a number") from exc
            value = ""

        date_tail, time_tail = (tail, value) if stream is time else (value, None)
        try:
            if date_tail:
                components = cls._fromdatestring(date_tail)
                measurements |= cls._filter(components, inclusive_range=True)
            if time_tail:
                components = cls._fromtimestring(time_tail)
                measurements |= cls._filter(components, inclusive_range=False)
        except ValueError as exc:
            raise _parse_error(exc) from None

        if not measurements:
            raise _parse_error("no measurements found")
        if "weeks" in measurements and len(measurements) > 1:
            raise _parse_error("cannot mix weeks with other units")
        if (
            stream is time
            and "hours" not in measurements
            and "minutes" not in measurements
            and "seconds" not in measurements
        ):
            raise _parse_error("no measurements found in time segment")

        try:
            return cls(**{k: v for k, v in measurements.items() if v})
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
