import sys

import pytz
from ..parser import ChatThread, ChatMessage, FacebookChatHistory


class UnserializableObject(Exception):
    pass

DATE_DOC_FORMAT = "%Y-%m-%dT%H:%M"


class Writer(object):

    def write(self, data, stream=sys.stdout):
        if isinstance(data, FacebookChatHistory):
            return self.write_history(data, stream)
        elif isinstance(data, ChatThread):
            return self.write_thread(data, stream)
        elif isinstance(data, ChatMessage):
            return self.write_message(data, stream)
        else:
            raise UnserializableObject()

    def write_history(self, data, stream):
        raise NotImplementedError

    def write_thread(self, data, stream):
        raise NotImplementedError

    def write_message(self, data, stream):
        raise NotImplementedError

    def timestamp_to_string(self, timestamp):
        timestamp_string = timestamp.strftime(DATE_DOC_FORMAT)
        tz_string = str(timestamp.tzinfo)
        if timestamp.tzinfo == pytz.utc:
            return "%sZ" % timestamp_string
        return "%s%s" % (timestamp_string, tz_string)
