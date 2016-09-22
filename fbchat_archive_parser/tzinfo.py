import datetime

_MIN_VALID_TIMEDELTA = datetime.timedelta(hours=-12)
_MAX_VALID_TIMEDELTA = datetime.timedelta(hours=14)


class TzInfoByOffset(datetime.tzinfo):
    """
    Basic timezone implementation (only found in datetime in Python 3+)
    """
    def __init__(self, time_delta):
        super(TzInfoByOffset, self).__init__()
        if not isinstance(time_delta, datetime.timedelta):
            raise ValueError("expected datetime.timedelta")
        if time_delta < _MIN_VALID_TIMEDELTA or \
           time_delta > _MAX_VALID_TIMEDELTA:
            raise ValueError("outside valid timezone range")
        self.time_delta = time_delta

    def utcoffset(self, dt):
        return self.time_delta

    def dst(self, dt):
        return datetime.timedelta(seconds=0)

    def tzname(self, dt):
        hours, seconds = divmod(self.time_delta.seconds, 3600)
        hours += self.time_delta.days * 24
        minutes, _ = divmod(seconds, 60)
        return "%s%02d:%02d" % ('+' if hours > -1 else '-',
                                abs(hours), abs(minutes))

    def __str__(self):
        return self.tzname(self)

    def __unicode__(self):
        return unicode(str(self))
