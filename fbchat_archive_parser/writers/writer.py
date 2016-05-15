from ..parser import ChatThread, ChatMessage, FacebookChatHistory


class UnserializableObject(Exception):
    pass


class Writer(object):

    DATE_DOC_FORMAT = "%Y-%m-%dT%H:%MZ"

    def write(self, data):
        if isinstance(data, FacebookChatHistory):
            return self.write_history(data)
        elif isinstance(data, ChatThread):
            return self.write_thread(data)
        elif isinstance(data, ChatMessage):
            return self.write_message(data)
        else:
            raise UnserializableObject

    def write_history(self, data):
        raise NotImplementedError

    def write_thread(self, data):
        raise NotImplementedError

    def write_message(self, data):
        raise NotImplementedError
