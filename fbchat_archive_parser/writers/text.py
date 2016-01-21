from __future__ import unicode_literals
from .writer import Writer

import sys
import csv

THREAD_ID_KEY = "thread"
SENDER_KEY = "sender"
DATE_KEY = "date"
MESSAGE_KEY = "message"

class TextWriter(Writer):


    def write_history(self, history, stream=sys.stdout):

        stream.write("Conversation history of %s\n\n" + history.user)

        for _, thread in history.iteritems():
            self.write_thread(thread, stream)

    def write_thread(self, thread, stream=sys.stdout):

        stream.write("Conversation with %s:\n\n" % ", ".join(thread.participants))

        for message in thread.messages:
            self.write_message(message, stream)

    def write_message(self, message, stream=sys.stdout):

        lines = message.content.split('\n') if message.content else [""]

        stream.write("[%s] %s: " % 
            (message.timestamp.strftime(self.DATE_DOC_FORMAT), message.sender))

        if len(lines) == 1:
            stream.write('%s\n' % lines[0])
        else:
            stream.write('\n\n')
            for line in lines:
                stream.write("    %s\n" % line)
            stream.write('\n')

