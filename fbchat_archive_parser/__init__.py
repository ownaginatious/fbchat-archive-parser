from collections import namedtuple

from sortedcontainers import SortedList

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions


class FacebookChatHistory:
    """
    Represents the Facebook chat history between the owner of
    the history and their contacts.
    """
    def __init__(self, user, threads=None):
        self.threads = threads if threads else {}
        self.user = user


class ChatThread(object):
    """
    Represents a chat thread between the owner of the history
    and a list of participants. Messages are stored in sorted
    order.
    """
    def __init__(self, participants):
        self.participants = list(participants)
        self.participants.sort()
        self.messages = SortedList()

    def add_message(self, message):
        """
        Adds a message to the chat thread.

        message -- the message to add
        """
        self.messages.add(message)
        return self

    def __lt__(self, other):
        return len(self.messages) < len(other.messages)

    def __len__(self):
        return len(self.messages)


# More recent messages have a lower magnitude sequence number.
_ChatMessageT = namedtuple('_ChatMessageT',
                           ['timestamp', 'seq_num', 'sender', 'content'])


class ChatMessage(_ChatMessageT):
    """
    A chat message from some recipient at
    a timestamp. Messages can also contain a sequence
    number for ordering messages that occurred the same time.
    """
    def __new__(cls, timestamp, sender, content, seq_num=0):
        """
        timestamp -- the time the message was sent (datetime)
        sender    -- who sent the message (unicode py2/str py3)
        content   -- content of the message (unicode py2/str py3)
        seq_num  -- sequence (default 0)
        """
        return super(ChatMessage, cls) \
            .__new__(cls, timestamp, seq_num, sender, content)
