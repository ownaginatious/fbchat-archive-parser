from __future__ import unicode_literals, absolute_import
from .writer import Writer

USER_KEY = "user"
THREADS_KEY = "threads"
SENDER_KEY = "sender"
DATE_KEY = "date"
MESSAGE_KEY = "message"
MESSAGES_KEY = "messages"
PARTICIPANTS_KEY = "participants"


class DictWriter(Writer):

    def serialize_content(self, data):
        raise NotImplementedError()

    def _write(self, stream, data):
        if stream:
            stream.write(self.serialize_content(data))
        return data

    def write_history(self, history, stream):

        threads = []

        for k in history.threads.keys():
            threads += [self.write_thread(history.threads[k], None)]

        content = {
            USER_KEY: history.user,
            THREADS_KEY: threads
        }
        return self._write(stream, content)

    def write_thread(self, thread, stream):

        messages = []

        for message in thread.messages:
            messages += [self.write_message(message, None)]

        content = {
            PARTICIPANTS_KEY: thread.participants,
            MESSAGES_KEY: messages
        }
        return self._write(stream, content)

    def write_message(self, message, stream):
        content = {
            SENDER_KEY: message.sender,
            DATE_KEY: self.timestamp_to_string(message.timestamp),
            MESSAGE_KEY: message.content
        }
        return self._write(stream, content)
