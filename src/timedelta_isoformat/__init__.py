import datetime


class timedelta(datetime.timedelta):
    @classmethod
    def fromisoformat(cls, duration_string):
        pass

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
