from __future__ import unicode_literals, absolute_import

import csv

from io import TextIOWrapper
import six

from ..utils import BinaryStreamWrapper
from .writer import Writer

THREAD_ID_KEY = "thread"
SENDER_KEY = "sender"
DATE_KEY = "date"
MESSAGE_KEY = "message"


class CsvWriter(Writer):

    def get_writer(self, stream, include_id=False):

        columns = [SENDER_KEY, DATE_KEY, MESSAGE_KEY]

        if include_id:
            columns = [THREAD_ID_KEY] + columns

        # Get the original stream back since CSV can't be in color anyway.
        if isinstance(stream, BinaryStreamWrapper):
            stream = stream.binary_stream

        # Python 2's CSV writer only works with bytes. In that case, let's
        # give it the underlying byte stream and encode keys/values to
        # UTF-8 ourselves so that it won't attempt to encode them using the
        # `ascii` encoder.
        if six.PY2:
            from encodings.utf_8 import StreamWriter
            if isinstance(stream, StreamWriter):  # TTY/piped writing
                stream = stream.stream
            elif isinstance(stream, TextIOWrapper):  # Direct file writing.
                stream = stream.buffer

        w = csv.DictWriter(stream,
                           fieldnames=columns,
                           quoting=csv.QUOTE_MINIMAL,
                           extrasaction="ignore",
                           lineterminator="\n")

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
        if six.PY2:
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

    @property
    def extension(self):
        return 'csv'
