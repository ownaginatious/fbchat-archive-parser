# -*- coding: utf-8 -*-

from datetime import datetime
import unittest

import pytz
from fbchat_archive_parser.time import (parse_timestamp,
                                        UnexpectedTimeFormatError,
                                        AmbiguousTimeZoneError)


class TestTimestamps(unittest.TestCase):

    def setUp(self):
        self.expected_datetime = datetime(2016, 12, 4, 20, 54).replace(tzinfo=pytz.UTC)

    def run_timestamp_test(self, timestamp_raw):
        timestamp = parse_timestamp(timestamp_raw, use_utc=True, hints={})
        self.assertEqual(self.expected_datetime, timestamp)

    def test_english_us_12(self):
        timestamp_raw = "Sunday, December 4, 2016 at 1:54pm PDT"
        self.run_timestamp_test(timestamp_raw)

    def test_english_us_24(self):
        timestamp_raw = "Sunday, December 4, 2016 at 13:54 PDT"
        self.run_timestamp_test(timestamp_raw)

    def test_english_uk_24(self):
        timestamp_raw = "Sunday, 4 December 2016 at 13:54 PDT"
        self.run_timestamp_test(timestamp_raw)

    def test_deutsch(self):
        timestamp_raw = "Sonntag, 4. Dezember 2016 um 13:54 PDT"
        self.run_timestamp_test(timestamp_raw)

    def test_norsk_bokmal(self):
        timestamp_raw = "4. desember 2016 kl. 13:54 UTC-07"
        self.run_timestamp_test(timestamp_raw)

    def test_bad_timestamp(self):
        timestamp_raw = "not a real timestamp"
        with self.assertRaises(UnexpectedTimeFormatError):
            self.run_timestamp_test(timestamp_raw)

    def test_ambiguous_timestamp(self):
        timestamp_raw = "Sunday, December 4, 2016 at 1:54pm CDT"
        with self.assertRaises(AmbiguousTimeZoneError):
            self.run_timestamp_test(timestamp_raw)

if __name__ == '__main__':
    unittest.main()
