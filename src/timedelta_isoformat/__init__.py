import datetime

_DIGITS, _DECIMAL_SIGNS = frozenset("0123456789"), frozenset(",.")
_FORMAT = _DIGITS | _DECIMAL_SIGNS


class timedelta(datetime.timedelta):
    @classmethod
    def fromisoformat(cls, duration):
        def _parse_error(reason):
            return ValueError(f"could not parse duration '{duration}': {reason}")

        if not duration.startswith("P"):
            raise _parse_error("durations must begin with the character 'P'")

        date_tokens = iter(("Y", "years", "M", "months", "D", "days"))
        time_tokens = iter(("H", "hours", "M", "minutes", "S", "seconds"))
        week_tokens = iter(("W", "weeks"))

        tokens, value, measurements = date_tokens, "", {}
        for char in duration[1:]:
            if char in _FORMAT:
                value += char
                continue

            if char == "T":
                tokens = time_tokens
                continue

            if char == "W":
                tokens = week_tokens
                pass

            # Note: this advances and may exhaust the iterator
            if char not in tokens:
                raise _parse_error(f"unexpected character '{char}'")

            if not value:
                raise _parse_error(f"missing measurement before character '{char}'")

            unit = next(tokens)
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
