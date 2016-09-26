import unittest
import os
from fbchat_archive_parser.parser import MessageHtmlParser

package_dir = os.path.dirname(os.path.abspath(__file__))


class TestDataStructures(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        parser = MessageHtmlParser(
                    os.path.join(package_dir, "simulated_data.htm"))
        cls.fbc = parser.parse()

    def test_num_threads(self):
        self.assertEqual(len(self.fbc.threads), 3)

    def test_thread_participants(self):

        expected = [
            ["Third User", ],
            ["Second User", ],
            ["Third User", "Second User"],
        ]

        expected = sorted(sorted(x) for x in expected)
        actual = [sorted(t.participants) for _, t in self.fbc.threads.items()]
        actual.sort()
        self.assertEqual(expected, actual)

    def test_message_content(self):
        pass

if __name__ == '__main__':
    unittest.main()
