# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import arrow
from collections import defaultdict
from datetime import datetime, tzinfo, timedelta as dt_timedelta
import pytz
from pytz import timezone as pytz_timezone

_MIN_VALID_TIMEZONE_OFFSET = dt_timedelta(hours=-12)
_MAX_VALID_TIMEZONE_OFFSET = dt_timedelta(hours=14)

# Timestamp formats (language_code, format string)
FACEBOOK_TIMESTAMP_FORMATS = [
    ("en_us", "dddd, MMMM D, YYYY [at] h:mmA"),  # English US (12-hour)
    ("en_us", "dddd, MMMM D, YYYY [at] HH:mm"),  # English US (24-hour)
    ("en_us", "dddd, D MMMM YYYY [at] HH:mm"),   # English UK (24-hour)
    ("fr_fr", "dddd D MMMM YYYY, HH:mm"),        # French (France)
    ("de_de", "dddd, D. MMMM YYYY [um] HH:mm"),  # German (Germany)
    ("nb_no", "D. MMMM YYYY kl. HH:mm"),         # Norwegian (Bokmål)
]

# Generate a mapping of all timezones to their offsets.
#
#  e.g. {
#          'PST': {
#              (-7, 0): ['Pacific/US', ...]
#           }
#       }
TIMEZONE_MAP = defaultdict(lambda: defaultdict(set))
for tz_name in pytz.all_timezones:
    recorded_codes = set()
    now = datetime.now()
    # This is a stupid way of detecting the codes for daylight savings time, but timezones in
    # general are stupid and this is an easy way.
    for d in range(0, 365, 30):
        # Sometimes we can come up with invalid days/times. We will try adding a day if that happens.
        try:
            tz = pytz_timezone(tz_name).localize(datetime.now() + dt_timedelta(days=d), is_dst=None)
        except pytz.exceptions.NonExistentTimeError:
            tz = pytz_timezone(tz_name).localize(datetime.now() + dt_timedelta(days=d + 1), is_dst=None)
        timezone_code = tz.strftime("%Z")
        if tz_name in recorded_codes:
            continue
        offset_raw = tz.strftime("%z")
        if offset_raw[0] == '-':
            offset = (-1 * int(offset_raw[1:3]), -1 * int(offset_raw[3:5]))
        else:
            offset = (int(offset_raw[1:3]), int(offset_raw[3:5]))
        offset += (offset_raw,)
        TIMEZONE_MAP[timezone_code][offset].add(tz_name)


class UnexpectedTimeFormatError(Exception):
    def __init__(self, time_string):
        self.time_string = time_string
        super(UnexpectedTimeFormatError, self).__init__()


class AmbiguousTimeZoneError(Exception):

    def __init__(self, tz_name, tz_options):
        self.tz_name = tz_name
        self.tz_options = tz_options
        super(AmbiguousTimeZoneError, self).__init__()


class TzInfoByOffset(tzinfo):
    """
    Basic timezone implementation (only found in datetime in Python 3+)
    """
    def __init__(self, time_delta):
        super(TzInfoByOffset, self).__init__()
        if not isinstance(time_delta, dt_timedelta):
            raise ValueError("expected datetime.timedelta")
        if time_delta < _MIN_VALID_TIMEZONE_OFFSET or \
           time_delta > _MAX_VALID_TIMEZONE_OFFSET:
            raise ValueError("outside valid timezone range")
        self.time_delta = time_delta

    def utcoffset(self, dt):
        return self.time_delta

    def dst(self, dt):
        return dt_timedelta(seconds=0)

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


def parse_timestamp(raw_timestamp, use_utc, hints):
    """
    Facebook is highly inconsistent with their timezone formatting.
    Sometimes it's in UTC+/-HH:MM form, and other times its in the
    ambiguous PST, PDT. etc format.

    We have to handle the ambiguity by asking for cues from the user.

    raw_timestamp -- The timestamp string to parse and convert to UTC.
    """
    global FACEBOOK_TIMESTAMP_FORMATS
    timestamp_string, offset = raw_timestamp.rsplit(" ", 1)
    if "UTC+" in offset or "UTC-" in offset:
        if offset[3] == '-':
            offset = [-1 * int(x) for x in offset[4:].split(':')]
        else:
            offset = [int(x) for x in offset[4:].split(':')]
    else:
        offset_hint = hints.get(offset, None)
        if not offset_hint:
            if offset not in TIMEZONE_MAP:
                raise UnexpectedTimeFormatError(raw_timestamp)
            elif len(TIMEZONE_MAP[offset]) > 1:
                raise AmbiguousTimeZoneError(offset, TIMEZONE_MAP[offset])
            offset = list(TIMEZONE_MAP[offset].keys())[0][:2]
        else:
            offset = offset_hint

    if len(offset) == 1:
        # Timezones without minute offset may be formatted
        # as UTC+X (e.g UTC+8)
        offset += [0]

    delta = dt_timedelta(hours=offset[0], minutes=offset[1])

    # Facebook changes the format depending on whether the user is using
    # 12-hour or 24-hour clock settings.
    timestamp = None
    for number, (language_code, time_format) in enumerate(FACEBOOK_TIMESTAMP_FORMATS):
        try:
            timestamp = arrow.get(timestamp_string, time_format, locale=language_code)
            # Re-orient the list to ensure that the one that worked is tried first next time.
            if number > 0:
                del FACEBOOK_TIMESTAMP_FORMATS[number]
                FACEBOOK_TIMESTAMP_FORMATS = [(language_code, time_format)] + FACEBOOK_TIMESTAMP_FORMATS
            break
        except arrow.parser.ParserError:
            pass

    if timestamp is None:
        raise UnexpectedTimeFormatError(raw_timestamp)
    timestamp = timestamp.datetime
    if use_utc:
        timestamp -= delta
        return timestamp.replace(tzinfo=pytz.utc)
    else:
        return timestamp.replace(tzinfo=TzInfoByOffset(delta))
