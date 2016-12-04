from __future__ import unicode_literals, absolute_import
from .writer import Writer

import csv
import sys

THREAD_ID_KEY = "thread"
SENDER_KEY = "sender"
DATE_KEY = "date"
MESSAGE_KEY = "message"


class CsvWriter(Writer):

    def get_writer(self, stream, include_id=False):

        columns = [SENDER_KEY, DATE_KEY, MESSAGE_KEY]

        if include_id:
            columns = [THREAD_ID_KEY] + columns

        # Python 2's CSV writer tries to handle encoding unicode itself.
        # In that case, let's give it the underlying byte stream and encode
        # keys/values to UTF-8 ourselves so that it won't attempt to encode
        # them.
        if sys.version_info[0] == 2:
            from encodings.utf_8 import StreamWriter
            if isinstance(stream, StreamWriter):
                stream = stream.stream

        w = csv.DictWriter(stream,
                           fieldnames=columns,
                           quoting=csv.QUOTE_MINIMAL,
                           extrasaction="ignore")

        w.writeheader()
        return w

    def write_history(self, history, stream, writer=None):
        if not writer:
            writer = self.get_writer(stream, True)
        for k in history.threads.keys():
            self.write_thread(history.threads[k], stream, writer=writer)

    def write_thread(self, thread, stream, writer=None):
        if not writer:
            writer = self.get_writer(stream, True)
        for message in thread.messages:
            self.write_message(message, stream, thread, writer=writer)

    def encode_row(self, row):
        if sys.version_info[0] == 2:
            return {
                k: v.encode('utf8')
                for k, v in row.items()
            }
        else:
            return row

    def write_message(self, message, stream, parent=None, writer=None):
        if not writer:
            writer = self.get_writer(stream, True)
        row = {
            SENDER_KEY: message.sender,
            DATE_KEY: self.timestamp_to_string(message.timestamp),
            MESSAGE_KEY: message.content
        }
        if parent:
            row[THREAD_ID_KEY] = "<unknown>" if not parent \
                                 else ", ".join(parent.participants)
        writer.writerow(self.encode_row(row))
