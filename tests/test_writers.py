# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from datetime import datetime
from io import BytesIO
import unittest

import pytz
import six


from fbchat_archive_parser import (FacebookChatHistory, ChatThread, ChatMessage)
from fbchat_archive_parser.writers import write


_NOW = datetime.now().replace(tzinfo=pytz.UTC)


class TestWriters(unittest.TestCase):

    def setUp(self):

        threads = {
            'test_owner,test_user': ChatThread(participants=['test_owner', 'test_user'])
                .add_message(ChatMessage(_NOW, 'test_owner', '白人看不懂', 0)),
            'test_user,test_user_1,test_user_2': ChatThread(participants=['test_owner', 'test_user_1', 'test_user_2'])
                .add_message(ChatMessage(_NOW, 'test_owner', '白人看不懂', 1))
                .add_message(ChatMessage(_NOW, 'test_user_1', 'Что это?', 2))
                .add_message(ChatMessage(_NOW, 'test_user_2', 'En ymmärrä', 2)),
        }

        self.history = FacebookChatHistory(user="test_owner", threads=threads)
        self.output = BytesIO()

        if six.PY3:
            import io
            self.output_handle = io.TextIOWrapper(self.output, encoding='UTF-8', errors='replace')
        else:
            from encodings.utf_8 import StreamWriter
            self.output_handle = StreamWriter(self.output)

    def assert_output(self, format, expected=None):
        write(format, self.history, stream_or_dir=self.output_handle)
        self.output_handle.flush()
        if expected is not None:
            self.assertEqual(expected, self.output.getvalue())

    def test_json(self):
        # TODO: Write tests for json expected output.
        self.assert_output('json')

    def test_csv(self):
        # TODO: Write tests for csv expected output.
        self.assert_output('csv')

    def test_yaml(self):
        # TODO: Write tests for yaml expected output.
        self.assert_output('yaml')

    def test_text(self):
        # TODO: Write tests for text expected output.
        self.assert_output('text')


if __name__ == '__main__':
    unittest.main()
