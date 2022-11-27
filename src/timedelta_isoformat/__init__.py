"""Supplemental ISO8601 duration format support for :py:class:`datetime.timedelta`"""
import datetime
from string import digits

_FIELD_CHARACTERS = frozenset(digits + ",-.:")

_DATE_UNITS = {
    "Y": "years",
    "M": "months",
    "D": "days",
}
_TIME_UNITS = {
    "H": "hours",
    "M": "minutes",
    "S": "seconds",
}
_WEEK_UNITS = {
    "W": "weeks",
}


class timedelta(datetime.timedelta):
    """Subclass of :py:class:`datetime.timedelta` with additional methods to implement
    ISO8601-style parsing and formatting.
    """

    @staticmethod
    def _filter(components):
        for quantity, unit, limit in components:
            if limit and quantity > limit:
                raise ValueError(f"{unit} value of {quantity} exceeds range 0..{limit}")
            yield unit, quantity

    @staticmethod
    def _fromdatestring(date_string):
        if not date_string:
            return

        found = False
        separator_positions = [i for i, c in enumerate(date_string) if c == "-"]
        date_length = len(date_string)

        # YYYY-DDD
        if date_length == 8 and separator_positions == [4]:
            yield int(date_string[0:4]), "years", None
            yield int(date_string[5:8]), "days", 366
            found = True

        # YYYY-MM-DD
        if date_length == 10 and separator_positions == [4, 7]:
            yield int(date_string[0:4]), "years", None
            yield int(date_string[5:7]), "months", 12
            yield int(date_string[8:10]), "days", 31
            found = True

        # YYYYDDD
        if date_length == 7 and separator_positions == []:
            yield int(date_string[0:4]), "years", None
            yield int(date_string[4:7]), "days", 366
            found = True

        # YYYYMMDD
        if date_length == 8 and separator_positions == []:
            yield int(date_string[0:4]), "years", None
            yield int(date_string[4:6]), "months", 12
            yield int(date_string[6:8]), "days", 31
            found = True

        if not found:
            raise ValueError(f"unable to parse '{date_string}' into date components")

    @staticmethod
    def _fromtimestring(time_string):
        if not time_string:
            return

        found = False
        separator_positions = [i for i, c in enumerate(time_string) if c == ":"]

        # HH:MM:SS[.ssssss]
        if separator_positions == [2, 5]:
            seconds_type = float if time_string[8:9] == "." else int
            yield int(time_string[0:2]), "hours", 23
            yield int(time_string[3:5]), "minutes", 59
            yield seconds_type(time_string[6:]), "seconds", 59
            found = True

        # HHMMSS[.ssssss]
        if separator_positions == []:
            seconds_type = float if time_string[6:7] == "." else int
            yield int(time_string[0:2]), "hours", 23
            yield int(time_string[2:4]), "minutes", 59
            yield seconds_type(time_string[4:]), "seconds", 59
            found = True

        if not found:
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

        date_designators = iter(("Y", "M", "D"))
        time_designators = iter(("H", "M", "S"))
        week_designators = iter(("W",))

        designators, units = date_designators, _DATE_UNITS

        value, measurements, segments = "", {}, {}
        while char := next(input_stream, None):
            if char in _FIELD_CHARACTERS:
                value += char
                continue

            if char == "T":
                segments[designators], value = value, ""
                designators, units = time_designators, _TIME_UNITS
                continue

            if char == "W":
                designators, units = week_designators, _WEEK_UNITS

            # Note: this advances and may exhaust the iterator
            if char not in designators:
                raise _parse_error(f"unexpected character '{char}'")

            if not value:
                raise _parse_error(f"missing measurement before character '{char}'")

            if not value[0].isdigit():
                raise _parse_error(f"value '{value}' does not start with a digit")

            try:
                quantity = float(value.replace(",", "."))
            except ValueError as exc:
                raise _parse_error(f"unable to parse '{value}' as a number") from exc
            measurements[units[char]] = quantity
            value = ""

        segments[designators] = value
        if any(segments.values()):
            if measurements:
                raise _parse_error("date segment format differs from time segment")
            for designators, value in segments.items():
                segment_parser = {
                    date_designators: cls._fromdatestring,
                    time_designators: cls._fromtimestring,
                    week_designators: lambda _: [],
                }[designators]
                measurements.update(cls._filter(segment_parser(value)))

        if not measurements:
            raise _parse_error("no measurements found")
        if not measurements.keys() & _TIME_UNITS.values() and units == _TIME_UNITS:
            raise _parse_error("no measurements found in time segment")
        if "weeks" in measurements and len(measurements) > 1:
            raise _parse_error("cannot mix weeks with other units")

        filtered_measurements = {k: v for k, v in measurements.items() if v}
        try:
            return cls(**filtered_measurements)
        except TypeError as exc:
            if filtered_measurements.keys() & {"years", "months"}:
                raise _parse_error("year and month fields are not supported") from exc
            raise exc

    def isoformat(self):
        """Produce an ISO8601-style representation of this :py:class:`timedelta`"""
        if not self:
            return "P0D"

        years, months, days = 0, 0, self.days
        hours, minutes, seconds = 0, 0, self.seconds
        minutes, seconds = int(seconds / 60), seconds % 60
        hours, minutes = int(minutes / 60), minutes % 60
        if self.microseconds:
            seconds += self.microseconds / 10 ** 6

        result = "P"
        result += f"{years}Y" if years else ""
        result += f"{months}M" if months else ""
        result += f"{days}D" if days else ""
        if hours or minutes or seconds:
            result += "T"
            result += f"{hours}H" if hours else ""
            result += f"{minutes}M" if minutes else ""
            result += f"{seconds}S" if seconds else ""
        return result
