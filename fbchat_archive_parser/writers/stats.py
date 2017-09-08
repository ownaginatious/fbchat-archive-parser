from __future__ import unicode_literals

from collections import Counter

from .writer import Writer
from ..utils import green, cyan, bright

THREAD_ID_KEY = "thread"
SENDER_KEY = "sender"
DATE_KEY = "date"
MESSAGE_KEY = "message"


class StatsWriter(Writer):

    DATE_DOC_FORMAT = "%Y-%m-%d %H:%MZ"

    def write_history(self, history, stream):

        text_string = '---------------' + \
                      ('-' * len(history.user)) + '--' + '\n'
        stream.write(bright(text_string))
        stream.write(bright(' Statistics for %s\n' % history.user))
        stream.write(bright(text_string))
        stream.write('\n')

        threads = tuple(history.threads[k] for k in history.threads.keys())
        stream.write('Top 10 longest threads:\n\n')
        ordered_threads = sorted(threads, key=lambda t: len(t))
        ordered_threads.reverse()
        for i, t in enumerate(ordered_threads[0:10], 1):
            stream.write("  " + cyan('[' + str(i) + '] ') +
                         bright(", ".join(t.participants) +
                                cyan(" (" + str(len(t.messages)) + ")" + "\n")))
            p_count = Counter()
            for m in t.messages:
                p_count[m.sender] += 1
            total = sum(p_count.values())
            for s, c in p_count.most_common():
                stream.write("      - " + s +
                             green(" [%d|%.2f%%]\n" % (c, (c * 100) / total)))
            stream.write('\n')

    @property
    def extension(self):
        return 'stats'
