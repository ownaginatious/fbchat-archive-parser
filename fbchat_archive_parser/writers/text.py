from __future__ import unicode_literals
from .writer import Writer
from colorama import Fore, Back, Style
import sys
import csv

THREAD_ID_KEY = "thread"
SENDER_KEY = "sender"
DATE_KEY = "date"
MESSAGE_KEY = "message"


class TextWriter(Writer):

    DATE_DOC_FORMAT = "%Y-%m-%d %H:%MZ"

    def write_history(self, history, stream=sys.stdout):

        stream.write(Back.BLACK + Fore.WHITE + "Conversation history of " +
                     Fore.CYAN + history.user + Fore.WHITE + "\n\n")

        for k in history.chat_threads.keys():
            self.write_thread(history.chat_threads[k], stream)

    def write_thread(self, thread, stream=sys.stdout):

        stream.write("\nConversation with %s:\n\n" %
                     (Fore.YELLOW +
                      ", ".join(thread.participants) +
                      Fore.WHITE))

        for message in thread.messages:
            self.write_message(message, stream)

    def write_message(self, message, stream=sys.stdout):

        lines = message.content.split('\n') if message.content else [""]

        stream.write((Style.DIM + "[%s] " +
                      Style.NORMAL + Fore.CYAN + "%s: " + Fore.WHITE) % (
                     message.timestamp.strftime(self.DATE_DOC_FORMAT),
                     message.sender))

        if len(lines) == 1:
            stream.write('%s\n' % lines[0])
        else:
            stream.write('\n\n')
            for line in lines:
                stream.write("    %s\n" % line)
            stream.write('\n')
