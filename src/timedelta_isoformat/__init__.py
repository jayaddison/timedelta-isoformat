"""Supplemental ISO8601 duration format support for :py:class:`datetime.timedelta`"""
import datetime


class timedelta(datetime.timedelta):
    """Subclass of :py:class:`datetime.timedelta` with additional methods to implement
    ISO8601-style parsing and formatting.
    """

    @staticmethod
    def _filter(components, inclusive_range=True):
        for quantity, unit, limit in components:
            if limit and (quantity > limit if inclusive_range else quantity >= limit):
                bounds = f"[0..{limit}" + ("]" if inclusive_range else ")")
                raise ValueError(f"{unit} value of {quantity} exceeds range {bounds}")
            yield unit, quantity

    @staticmethod
    def _fromdatestring(date_string):
        separator_positions = [i for i, c in enumerate(date_string) if c == "-"]
        date_length = len(date_string)

        # YYYY-DDD
        if date_length == 8 and separator_positions == [4]:
            yield int(date_string[0:4]), "years", None
            yield int(date_string[5:8]), "days", 366

        # YYYY-MM-DD
        elif date_length == 10 and separator_positions == [4, 7]:
            yield int(date_string[0:4]), "years", None
            yield int(date_string[5:7]), "months", 12
            yield int(date_string[8:10]), "days", 31

        # YYYYDDD
        elif date_length == 7 and separator_positions == []:
            yield int(date_string[0:4]), "years", None
            yield int(date_string[4:7]), "days", 366

        # YYYYMMDD
        elif date_length == 8 and separator_positions == []:
            yield int(date_string[0:4]), "years", None
            yield int(date_string[4:6]), "months", 12
            yield int(date_string[6:8]), "days", 31

        else:
            raise ValueError(f"unable to parse '{date_string}' into date components")

    @staticmethod
    def _fromtimestring(time_string):
        separator_positions = [i for i, c in enumerate(time_string) if c == ":"]

        # HH:MM:SS[.ssssss]
        if separator_positions == [2, 5]:
            yield int(time_string[0:2]), "hours", 24
            yield int(time_string[3:5]), "minutes", 60
            yield float(time_string[6:]), "seconds", 60

        # HHMMSS[.ssssss]
        elif separator_positions == []:
            yield int(time_string[0:2]), "hours", 24
            yield int(time_string[2:4]), "minutes", 60
            yield float(time_string[4:]), "seconds", 60

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

        stream, value, measurements = date, "", {}
        while char := next(input_stream, None):
            if char.isdigit() or char in ",-.:":
                value += char
                continue

            if char == "T" and stream is not time:
                if value:
                    components = cls._fromdatestring(value)
                    measurements.update(cls._filter(components, inclusive_range=False))
                    value = ""
                stream = time
                continue

            if char == "W" and stream is date:
                stream = week

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

        if value:
            segment_parsers = {
                date: cls._fromdatestring,
                time: cls._fromtimestring,
            }
            inclusive_ranges = {
                date: True,
                time: False,
            }
            components = segment_parsers[stream](value)
            measurements.update(cls._filter(components, inclusive_ranges[stream]))

        if not measurements:
            raise _parse_error("no measurements found")
        if stream is time and not measurements.keys() & {"hours", "minutes", "seconds"}:
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
        if hours or minutes or seconds:
            result += "T"
            result += f"{hours}H" if hours else ""
            result += f"{minutes}M" if minutes else ""
            result += f"{seconds:.6f}".rstrip("0").rstrip(".") + "S" if seconds else ""
        return result
