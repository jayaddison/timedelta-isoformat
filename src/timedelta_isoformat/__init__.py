import datetime
from string import digits

_NUMERIC_CHARACTERS = frozenset(digits + ",.")

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
    @classmethod
    def fromisoformat(cls, duration_string):
        def _parse_error(reason):
            return TypeError(f"could not parse duration '{duration_string}': {reason}")

        input_stream = iter(duration_string)
        if next(input_stream, None) != "P":
            raise _parse_error("durations must begin with the character 'P'")

        date_designators = iter(("Y", "M", "D"))
        time_designators = iter(("H", "M", "S"))
        week_designators = iter(("W",))

        designators, units = date_designators, _DATE_UNITS

        value, measurements = "", {}
        while char := next(input_stream, None):
            if char in _NUMERIC_CHARACTERS:
                value += char
                continue

            if char == "T":
                designators, units = time_designators, _TIME_UNITS
                continue

            if char == "W":
                designators, units = week_designators, _WEEK_UNITS

            # Note: this advances and may exhaust the iterator
            if char not in designators:
                raise _parse_error(f"unexpected character '{char}'")

            if not value:
                raise _parse_error(f"missing measurement before '{char}'")
            value, measurements[units[char]] = "", float(value)

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
