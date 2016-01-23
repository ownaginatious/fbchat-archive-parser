from __future__ import unicode_literals, absolute_import
from .writer import Writer

import sys
import json

USER_KEY = "user"
THREADS_KEY = "threads"
SENDER_KEY = "sender"
DATE_KEY = "date"
MESSAGE_KEY = "message"
MESSAGES_KEY = "messages"
PARTICIPANTS_KEY = "participants"


class JsonWriter(Writer):

    def write_history(self, history, stream=sys.stdout):

        threads = []

        for k in history.chat_threads.keys():
            threads += [self.write_thread(history.chat_threads[k], None)]

        content = {
            USER_KEY: history.user,
            THREADS_KEY: threads
        }

        stream.write(json.dumps(content))

    def write_thread(self, thread, stream=sys.stdout):

        messages = []

        for message in thread.messages:
            messages += [self.write_message(message, None)]

        content = {
            PARTICIPANTS_KEY: thread.participants,
            MESSAGES_KEY: messages
        }

        if not stream:
            return content

        stream.write(json.dumps(content))

    def write_message(self, message, stream=sys.stdout):

        content = {
            SENDER_KEY: message.sender,
            DATE_KEY: message.timestamp.strftime(self.DATE_DOC_FORMAT),
            MESSAGE_KEY: message.content
        }

        if not stream:
            return content

        stream.write(json.dumps(content))
