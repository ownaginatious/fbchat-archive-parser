from __future__ import unicode_literals

from .writer import Writer
from ..utils import yellow, red, cyan, bright

THREAD_ID_KEY = "thread"
SENDER_KEY = "sender"
DATE_KEY = "date"
MESSAGE_KEY = "message"


class TextWriter(Writer):

    DATE_DOC_FORMAT = "%Y-%m-%d %H:%MZ"

    def write_history(self, history, stream):

        dash_line = "-------------------------" + \
                    ('-' * len(history.user)) + "-\n"

        stream.write(bright(dash_line))
        stream.write(bright(" Conversation history of %s\n")
                     % cyan(history.user))
        stream.write(bright(dash_line))

        if len(history.threads) > 0:
            for k in sorted([k for k in history.threads.keys()]):
                self.write_thread(history.threads[k], stream)
        else:
            stream.write("\n   There's nothing here!\n")
        stream.write("\n")

    def write_thread(self, thread, stream):

        stream.write("\nConversation with %s:\n\n" %
                     yellow(", ".join(thread.participants)))
        for message in thread.messages:
            self.write_message(message, stream)

    def write_message(self, message, stream):

        lines = message.content.split('\n') if message.content else [""]

        stream.write((red("[%s] ") + cyan("%s: ")) % (
                     self.timestamp_to_string(message.timestamp),
                     message.sender))

        if len(lines) == 1:
            stream.write('%s\n' % lines[0])
        else:
            stream.write('\n\n')
            for line in lines:
                stream.write("    %s\n" % line)
            stream.write('\n')
