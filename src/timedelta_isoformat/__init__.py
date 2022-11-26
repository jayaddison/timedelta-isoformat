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
    @staticmethod
    def _filter(segments):
        for quantity, unit, limit in segments:
            if limit and quantity > limit:
                raise ValueError(f"{unit} value of {quantity} exceeds range 0..{limit}")
            if quantity != 0:
                yield unit, quantity

    @staticmethod
    def _fromdatestring(date_string):
        if not date_string:
            return

        date_length = len(date_string)

        # YYYY-DDD or YYYY-MM-DD
        if date_string[4] == "-" and date_length in (8, 10):
            if date_length == 8:
                yield int(date_string[0:4]), "years", None
                yield int(date_string[5:8]), "days", 365
                return
            else:
                yield int(date_string[0:4]), "years", None
                yield int(date_string[5:7]), "months", 12
                yield int(date_string[8:10]), "days", 31
                return

        # YYYYDDD or YYYYMMDD
        else:
            if len(date_string) == 7:
                yield int(date_string[0:4]), "years", None
                yield int(date_string[4:7]), "days", 365
                return
            else:
                yield int(date_string[0:4]), "years", None
                yield int(date_string[4:6]), "months", 12
                yield int(date_string[6:8]), "days", 31
                return

        raise ValueError()

    @staticmethod
    def _fromtimestring(time_string):
        if not time_string:
            return

        # HH:MM:SS[.ssssss]
        if time_string[2] == ":":
            yield int(time_string[0:2]), "hours", 24
            yield int(time_string[3:5]), "minutes", 60
            yield float(time_string[6:]), "seconds", 60
            return

        # HHMMSS[.ssssss]
        else:
            yield int(time_string[0:2]), "hours", 24
            yield int(time_string[2:4]), "minutes", 60
            yield float(time_string[4:]), "seconds", 60
            return

        raise ValueError()

    @classmethod
    def fromisoformat(cls, duration_string):
        def _parse_error(reason):
            return ValueError(f"could not parse duration '{duration_string}': {reason}")

        input_stream = iter(duration_string)
        if next(input_stream, None) != "P":
            raise _parse_error("durations must begin with the character 'P'")

        date_designators = iter(("Y", "M", "D"))
        time_designators = iter(("H", "M", "S"))
        week_designators = iter(("W",))

        designators, units = date_designators, _DATE_UNITS

        value, measurements = "", {}
        while char := next(input_stream, None):
            if char in _FIELD_CHARACTERS:
                value += char
                continue

            if char == "T":
                if value:
                    measurements.update(cls._filter(cls._fromdatestring(value)))
                    value = ""
                designators, units = time_designators, _TIME_UNITS
                continue

            if char == "W":
                designators, units = week_designators, _WEEK_UNITS

            # Note: this advances and may exhaust the iterator
            if char not in designators:
                raise _parse_error(f"unexpected character '{char}'")

            if not value:
                raise _parse_error(f"missing measurement before character '{char}'")

            try:
                quantity = float(value.replace(",", "."))
            except ValueError:
                raise _parse_error(f"unable to intepret '{value}' as a numeric value")
            value, measurements[units[char]] = "", quantity

        segments = cls._fromdatestring if units == _DATE_UNITS else cls._fromtimestring
        measurements.update(cls._filter(segments(value)))

        if not measurements:
            raise _parse_error("no measurements found")
        if "weeks" in measurements and len(measurements) > 1:
            raise _parse_error("cannot mix weeks with other units")
        return cls(**measurements)

    def isoformat(self):
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
