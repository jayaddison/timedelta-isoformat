import datetime


class timedelta(datetime.timedelta):
    @classmethod
    def fromisoformat(cls, duration_string):
        pass

    def isoformat(self):
        pass
