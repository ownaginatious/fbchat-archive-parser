import unittest
from datetime import datetime
from itertools import permutations
from fbchat_archive_parser.parser \
    import FacebookChatHistory, ChatThread, ChatMessage


class TestDataStructures(unittest.TestCase):

    def test_message_comparison(self):

        m1 = ChatMessage(datetime(2015, 1, 1, 0, 0), "Sender 1",
                         "Chat message 1", 0)

        m2 = ChatMessage(datetime(2015, 1, 1, 0, 0), "Sender 2",
                         "Chat message 2", 1)

        self.assertTrue(m2 < m1, "Message sequence ordering failed")

        # Order by time
        m2.timestamp = datetime(2015, 1, 1, 0, 1)
        self.assertTrue(m2 > m1, "Message time ordering failed")

    def test_thread_message_ordering(self):

        # Within thread
        m1 = ChatMessage(datetime(2015, 1, 1, 0, 0),
                         "Sender 1", "1", 3)
        m2 = ChatMessage(datetime(2015, 1, 2, 0, 0),
                         "Sender 2", "2", 1)
        m3 = ChatMessage(datetime(2015, 1, 2, 0, 0),
                         "Sender 3", "3", 2)

        for p in permutations([m1, m2, m3]):
            thread = ChatThread([])

            for m in p:
                thread.add_message(m)

            self.assertEqual([1, 3, 2],
                             [int(m.content) for m in thread.messages])

if __name__ == '__main__':
    unittest.main()
