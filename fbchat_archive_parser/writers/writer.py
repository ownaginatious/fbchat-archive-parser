import pytz
from ..parser import ChatThread, ChatMessage, FacebookChatHistory


class UnserializableObject(Exception):
    pass

DATE_DOC_FORMAT = "%Y-%m-%dT%H:%M"


class Writer(object):

    def write(self, data):
        if isinstance(data, FacebookChatHistory):
            return self.write_history(data)
        elif isinstance(data, ChatThread):
            return self.write_thread(data)
        elif isinstance(data, ChatMessage):
            return self.write_message(data)
        else:
            raise UnserializableObject()

    def write_history(self, data):
        raise NotImplementedError

    def write_thread(self, data):
        raise NotImplementedError

    def write_message(self, data):
        raise NotImplementedError

    def timestamp_to_string(self, timestamp):
        timestamp_string = timestamp.strftime(DATE_DOC_FORMAT)
        tz_string = str(timestamp.tzinfo)
        if timestamp.tzinfo == pytz.utc:
            return "%sZ" % timestamp_string
        return "%s%s" % (timestamp_string, tz_string)
