import unittest
import os
from fbchat_archive_parser.parser import FacebookChatHistory

package_dir = os.path.dirname(os.path.abspath(__file__))


class TestDataStructures(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fbc = FacebookChatHistory(
                    os.path.join(package_dir, "simulated_data.htm"))

    def test_num_threads(self):
        self.assertEqual(len(self.fbc.chat_threads), 3)

    def test_thread_participants(self):

        expected = [
            ["Third User", ],
            ["Second User", ],
            ["Third User", "Second User"],
        ]

        expected = sorted(sorted(x) for x in expected)
        actual = []

        for participants in self.fbc.chat_threads.keys():
            actual += [sorted(participants)]

        actual.sort()
        self.assertEqual(expected, actual)

    def test_message_content(self):
        pass

if __name__ == '__main__':
    unittest.main()
