from __future__ import unicode_literals
from .writer import Writer

import sys
import csv

THREAD_ID_KEY = "thread"
SENDER_KEY = "sender"
DATE_KEY = "date"
MESSAGE_KEY = "message"

class CsvWriter(Writer):

    def get_writer(self, stream, include_id=False):

        columns = [SENDER_KEY, DATE_KEY, MESSAGE_KEY]
        
        if include_id:
            columns = [THREAD_ID_KEY] + columns

        w = csv.DictWriter(stream,
            fieldnames=columns,
            quoting = csv.QUOTE_MINIMAL,
            extrasaction = "ignore")

        w.writeheader()
        return w

    def write_history(self, history, stream=sys.stdout, writer=None):
        if not writer:
            writer = self.get_writer(True)
        for _, thread in history.iteritems():
            self.write_thread(thread, writer)

    def write_thread(self, thread, stream=sys.stdout, writer=None):
        if not writer:
            writer = self.get_writer(True)
        for message in thread.messages:
            self.write_message(message, writer)

    def write_message(self, message, parent=None, stream=sys.stdout, writer=None):
        if not writer:
            writer = self.get_writer(True)
        row = {
            SENDER_KEY: message.sender,
            DATE_KEY: message.timestamp.strftime(self.DATE_DOC_FORMAT),
            MESSAGE_KEY: message.content
        }]
        if parent:
            row[THREAD_ID_KEY] = ", ".join(parent.participants),

        writer.writerow(row)
