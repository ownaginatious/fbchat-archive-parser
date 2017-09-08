import unittest
from datetime import datetime
from itertools import permutations
from fbchat_archive_parser import \
    FacebookChatHistory, ChatThread, ChatMessage


class TestDataStructures(unittest.TestCase):

    def test_message_comparison(self):

        m1 = ChatMessage(timestamp=datetime(2015, 1, 1, 0, 0),
                         seq_num=0,
                         sender="Sender 1",
                         content="Chat message 1")

        m2 = ChatMessage(timestamp=datetime(2015, 1, 1, 0, 0),
                         seq_num=-1,
                         sender="Sender 2",
                         content="Chat message 2")

        self.assertTrue(m2 < m1, "Message sequence ordering failed")

        # Order by time
        m2 = m2._replace(timestamp=datetime(2015, 1, 1, 0, 1))
        self.assertTrue(m2 > m1, "Message time ordering failed")

    def test_thread_message_ordering(self):

        # Within thread
        m1 = ChatMessage(timestamp=datetime(2015, 1, 1, 0, 0),
                         seq_num=-3,
                         sender="Sender 1",
                         content="1")
        m2 = ChatMessage(timestamp=datetime(2015, 1, 2, 0, 0),
                         seq_num=-1,
                         sender="Sender 2",
                         content="2")
        m3 = ChatMessage(timestamp=datetime(2015, 1, 2, 0, 0),
                         seq_num=-2,
                         sender="Sender 3",
                         content="3")

        for p in permutations([m1, m2, m3]):
            thread = ChatThread([])

            for m in p:
                thread.add_message(m)
            thread.messages.sort()

            self.assertEqual([1, 3, 2],
                             [int(m.content) for m in thread.messages])

if __name__ == '__main__':
    unittest.main()
