import datetime
from string import digits

_NUMERIC_CHARACTERS = frozenset(digits + ",.")


class timedelta(datetime.timedelta):
    @classmethod
    def fromisoformat(cls, duration_string):
        def _parse_error(reason):
            return ValueError(f"could not parse duration '{duration_string}': {reason}")

        if not duration_string.startswith("P"):
            raise _parse_error("durations must begin with the character 'P'")

        date_designators = iter(("Y", "years", "M", "months", "D", "days"))
        time_designators = iter(("H", "hours", "M", "minutes", "S", "seconds"))
        week_designators = iter(("W", "weeks"))

        designators, value, measurements = date_designators, "", {}
        for char in duration_string[1:]:
            if char in _NUMERIC_CHARACTERS:
                value += char
                continue

            if char == "T":
                designators = time_designators
                continue

            if char == "W":
                designators = week_designators
                pass

            # Note: this advances and may exhaust the iterator
            if char not in designators:
                raise _parse_error(f"unexpected character '{char}'")

            if not value:
                raise _parse_error(f"missing measurement before character '{char}'")

            unit = next(designators)
            try:
                measurements[unit] = float(value.replace(",", "."))
            except ValueError:
                raise _parse_error(f"unable to intepret '{value}' as a numeric value")
            value = ""

        if not measurements:
            raise _parse_error("no measurements found")
        if "weeks" in measurements and len(measurements) > 1:
            raise _parse_error("cannot mix weeks with other units")
        return cls(**measurements)

    def isoformat(self):
        if not self:
            return "P0D"

        days = self.days
        seconds = self.seconds

        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if self.microseconds:
            seconds += self.microseconds / 1_000_000  # type: ignore

        result = "P"
        result += f"{days}D" if days else ""
        if hours or minutes or seconds:
            result += "T"
            result += f"{hours}H" if hours else ""
            result += f"{minutes}M" if minutes else ""
            result += f"{seconds:.6f}".rstrip("0").rstrip(".") + "S" if seconds else ""
        return result
