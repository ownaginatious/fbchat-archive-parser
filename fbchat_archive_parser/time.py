# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from collections import defaultdict
from datetime import datetime, tzinfo, time, timedelta as dt_timedelta
import re

import pytz
from pytz.exceptions import NonExistentTimeError, AmbiguousTimeError
from pytz import timezone as pytz_timezone

import arrow
from babel import Locale

_MIN_VALID_TIMEZONE_OFFSET = dt_timedelta(hours=-12)
_MAX_VALID_TIMEZONE_OFFSET = dt_timedelta(hours=14)

# Timestamp formats (language_code, format string, [hints])
#
# "hints" is a dictionary of word -> int translations. Strongly inflected languages,
# such as the Slavic languages, tend to change the endings of day and month names to
# reflect grammatical cases.
#
# The supporting multi-lingual date libraries tend to screw this up a lot of the time,
# so you can add support for missing months. Facebook seems to mess it up on less popular
# languages too...
#
# Days of the week are 1 -> 7 (e.g. Monday -> 1) and months are 1 -> 12 (e.g. January -> 1)
#
# e.g. {'poniedziałek': 1}
#
FACEBOOK_TIMESTAMP_FORMATS = [
    ("en_us", "dddd, MMMM D, YYYY [at] h:mmA"),                 # English US (12-hour)
    ("en_us", "dddd, MMMM D, YYYY [at] HH:mm"),                 # English US (24-hour)
    ("en_us", "dddd, D MMMM YYYY [at] HH:mm"),                  # English UK (24-hour)
    ("fr_fr", "dddd D MMMM YYYY, HH:mm"),                       # French (France)
    ("de_de", "dddd, D. MMMM YYYY [um] HH:mm"),                 # German (Germany)
    ("nb_no", "D. MMMM YYYY [kl.] HH:mm"),                      # Norwegian (Bokmål)
    ("es_es", "dddd, D [de] MMMM [de] YYYY [a las?] H:mm"),     # Spanish (General)
    ("hu_hu", "YYYY. MMMM D., H:mm"),                           # Hungarian
    ("it_it", "dddd D MMMM YYYY [alle ore] H:mm"),              # Italian (Italy)
    ("sv_se", "D MMMM YYYY [kl.] HH:mm"),                       # Swedish (Sweden)
    ("nl_nl", "dddd D MMMM YYYY [om] H:mm"),                    # Dutch (Netherlands)
    ("da_dk", "D. MMMM YYYY [kl.] HH:mm"),                      # Danish (Denmark)
    ("ro_ro", "D MMMM YYYY [la] HH:mm"),                        # Romanian (Romania)
    ("sl_si", "D. MMMM YYYY [ob] H:mm"),                        # Slovenian
    ("cs_cz", "D. MMMM YYYY [v] H:mm"),                         # Czech
    ("pt_br", "D [de] MMMM [de] YYYY [às] HH:mm"),              # Portuguese (Brazil)
    ("pt_pt", "dddd, D [de] MMMM [de] YYYY [às] HH:mm"),        # Portuguese (Portugal)
    ("pl_pl", "D MMMM YYYY [o] HH:mm"),                         # Polish
    ("hr_hr", "D. MMMM YYYY [u] H:mm"),                         # Croatian
    ("sr_sr", "D. MMMM YYYY. [у] H:mm"),                        # Serbian (Cyrillic)
    ("fi_fi", "D. MMMM YYYY [kello] H:mm"),                     # Finnish
    ("ru_ru", "D MMMM YYYY [г. в] H:mm"),                       # Russian
]


class LocalizedDateParser(object):
    """
    Maps the day and month names back to numeric values for a provided locale code and performs
    parsing.
    """

    def __init__(self, locale_id, timestamp_format, hints=None):

        self.locale_id = locale_id
        self.use_fallback = False
        self.original_timestamp_format = timestamp_format
        self.timestamp_format = timestamp_format.replace('dddd', 'd').replace('MMMM', 'M')

        locale = Locale(locale_id.split('_')[0])
        self.translation_map = {k: str(v) for k, v in hints.items()} if hints else {}
        # Add in the month and day name data.
        for attr, start, end, offset in (('months', 1, 12, 0), ('days', 0, 6, 1)):
            for i in range(start, end + 1):
                attr_name = getattr(locale, attr)['format']['wide'][i]
                self.translation_map[attr_name.title()] = str(i + offset)
                self.translation_map[attr_name.lower()] = str(i + offset)
        self.matcher = re.compile('|'.join(self.translation_map.keys()))

    def _translate(self, timestamp):
        return self.matcher.sub(lambda match: self.translation_map[match.group(0)], timestamp)

    def _parse_fallback(self, timestamp):
        try:
            return arrow.get(timestamp,
                             self.original_timestamp_format,
                             locale=self.locale_id).datetime
        except arrow.parser.ParserError:
            return None

    def parse(self, timestamp):
        if self.use_fallback:
            return self._parse_fallback(timestamp)
        else:
            try:
                translated_timestamp = self._translate(timestamp)
                return arrow.get(translated_timestamp, self.timestamp_format).datetime
            except arrow.parser.ParserError:
                self.use_fallback = True
                try:
                    return self._parse_fallback(timestamp)
                except ValueError as ve:
                    self.use_fallback = False
                    if 'unsupported' not in str(ve).lower():
                        raise ve

_LOCALIZED_DATE_PARSERS = [
    LocalizedDateParser(x[0], x[1], x[2] if len(x) > 2 else {})
    for x in FACEBOOK_TIMESTAMP_FORMATS]

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
    now = datetime.combine(datetime(datetime.now().year, 1, 1).date(), time.min)
    # This is a stupid way of detecting the codes for daylight savings time, but timezones in
    # general are stupid and this is an easy way.
    for d in range(0, 365, 30):
        # Sometimes we can come up with invalid days/times. We will try adding a day if that happens.
        try:
            tz = pytz_timezone(tz_name).localize(now + dt_timedelta(days=d), is_dst=None)
        except (NonExistentTimeError, AmbiguousTimeError):
            tz = pytz_timezone(tz_name).localize(now + dt_timedelta(days=d + 1), is_dst=None)
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
        # Apparently Facebook also uses the literal names. Let's throw those in too.
        TIMEZONE_MAP[tz_name][offset] = set()


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
    for number, date_parser in enumerate(_LOCALIZED_DATE_PARSERS):
        timestamp = date_parser.parse(timestamp_string)
        if timestamp is None:
            continue
        # Re-orient the list to ensure that the one that worked is tried first next time.
        if number > 0:
            del FACEBOOK_TIMESTAMP_FORMATS[number]
            FACEBOOK_TIMESTAMP_FORMATS = [date_parser] + FACEBOOK_TIMESTAMP_FORMATS
        break
    else:
        raise UnexpectedTimeFormatError(raw_timestamp)
    if use_utc:
        timestamp -= delta
        return timestamp.replace(tzinfo=pytz.utc)
    else:
        return timestamp.replace(tzinfo=TzInfoByOffset(delta))
