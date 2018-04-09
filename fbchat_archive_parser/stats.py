from __future__ import unicode_literals

from collections import defaultdict, Counter

import json
import re
import yaml

import six

from .utils import bright, cyan, yellow, green


# This will match spaces and punctuation followed by spaces or nothing.
# This preserves things such as URLs in the output.
_PUNCTUATION_RE = r'[?!:;\'\".,&()\[\]-]'
_PUNCTUATION_POS_RE = re.compile(r'{} ?|{}$| '.format(_PUNCTUATION_RE, _PUNCTUATION_RE))


def extract_words(sentence):
    return (w.lower() for w in _PUNCTUATION_POS_RE.split(sentence) if w != '')


class UnsupportedStatsFormatError(Exception):
    pass


class ChatHistoryStatistics(object):

    DATE_DOC_FORMAT = "%Y-%m-%d %H:%MZ"

    def __init__(self, history, most_common=10):
        self.history = history
        self.most_common = most_common
        self._cached_history = None

    def _compute_message_stats(self, messages, for_participants):

        for_participants = set(for_participants)
        # Ensure all participants are accounted for, even if they
        # never said anything.
        results = defaultdict(lambda: {'messagesSent': 0})
        for participant in for_participants:
            _ = results[participant]

        word_stats = defaultdict(Counter)

        oldest_message, newest_message = None, None

        total_message_count = 0
        for message in messages:
            if not oldest_message or message.timestamp < oldest_message.timestamp:
                oldest_message = message
            if not newest_message or message.timestamp > newest_message.timestamp:
                newest_message = message
            sender = '{} participants'.format(
                'Other' if len(for_participants) else 'All')
            if message.sender in for_participants:
                sender = message.sender
            for word in extract_words(message.content):
                word_stats[sender][word] += 1
            results[sender]['messagesSent'] += 1
            total_message_count += 1

        # Calculate the post processing results for each participant.
        for participant, result in results.items():
            result['percentOfThread'] = '%.2f' % (
                (float(result['messagesSent'] * 100)) / total_message_count)
            result['mostCommonWords'] = list(
                w[0] for w in word_stats[participant].most_common(self.most_common or None))

        return {
            'participants': dict(results),
            'totalMessagesSent': total_message_count,
            'oldestMessage': {
                'date': oldest_message.timestamp.strftime(self.DATE_DOC_FORMAT),
                'sender': oldest_message.sender,
                'message': oldest_message.content
            },
            'newestMessage': {
                'date': newest_message.timestamp.strftime(self.DATE_DOC_FORMAT),
                'sender': newest_message.sender,
                'message': newest_message.content
            }
        }

    def _compute_global_stats(self):

        total_sent, total_received = 0, 0

        for thread in self.history.threads.values():
            for message in thread.messages:
                if message.sender == self.history.user:
                    total_sent += 1
                else:
                    total_received += 1

        threads_ordered_by_age = sorted(
            self.history.threads.values(), key=lambda t: t.messages[0].timestamp)

        results = {
            'forUser': self.history.user,
            'globalStats': self._compute_message_stats(
                messages=(m for t in self.history.threads.values() for m in t.messages),
                for_participants=[self.history.user]
            )
        }

        results['globalStats'].update({
            'totalConversations': len(self.history.threads),
            'oldestConversation': threads_ordered_by_age[0].participants,
            'newestConversation': threads_ordered_by_age[-1].participants,
        })
        return results

    def compute_stats(self):
        if self._cached_history:
            return self._cached_history
        results = self._compute_global_stats()
        results['conversationStats'] = [
            self._compute_message_stats(
                messages=v.messages,
                for_participants=v.participants + [self.history.user])
            for v in self.history.threads.values()
        ]
        friend_loudness = Counter()
        for r in results['conversationStats']:
            for k, v in r['participants'].items():
                if k == self.history.user:
                    continue
                friend_loudness[k] += v['messagesSent']
        loudest_friend = friend_loudness.most_common(1)[0]
        results['globalStats']['loudestFriend'] = {
            'name': loudest_friend[0],
            'messagesSent': loudest_friend[1]
        }
        results['conversationStats'].sort(key=lambda t: t['totalMessagesSent'])
        self._cached_history = results
        return results

    def write_text(self, stream, length):
        results = self.compute_stats()

        text_string = ('------------------------------------{}---\n'.format(
            '-' * len(results['forUser'])))
        stream.write(bright(text_string))
        stream.write(
            bright(' Conversation history statistics for {}\n'.format(results['forUser'])))
        stream.write(bright(text_string))
        stream.write('\n')

        stream.write('Global statistics:\n\n')
        stream.write('  - Total messages: {} [sent {} | received {}]\n'.format(
            cyan(results['globalStats']['totalMessagesSent']),
            cyan(results['globalStats']['participants'][results['forUser']]['messagesSent']),
            cyan(results['globalStats']['participants']['Other participants']['messagesSent'])
        ))
        stream.write('  - Total conversations: {}\n'.format(
            cyan(results['globalStats']['totalConversations'])))

        stream.write('  - Oldest conversation: {}\n'.format(yellow(
            ', '.join(results['globalStats']['oldestConversation']))))
        stream.write('  - Newest conversation: {}\n'.format(yellow(
            ', '.join(results['globalStats']['newestConversation']))))
        stream.write('  - Most talkative friend: {} [sent: {}]\n'.format(
            yellow(results['globalStats']['loudestFriend']['name']),
            cyan(results['globalStats']['loudestFriend']['messagesSent'])))
        stream.write('  - Most common words:\n')
        stream.write('     > {}: {}\n'.format(
            results['forUser'],
            ', '.join(results['globalStats'][
                          'participants'][results['forUser']]['mostCommonWords']))
        )
        stream.write('     > Everyone else: {}\n\n'.format(
            ', '.join(results['globalStats'][
                          'participants']['Other participants']['mostCommonWords']))
        )

        stream.write('Conversation statistics (ordered by descending length):\n\n')
        sorted_convos = sorted(
            results['conversationStats'], key=lambda e: -e['totalMessagesSent'])
        for i, e in enumerate(sorted_convos[0:length], 1):

            stream.write(' {} {}{}\n'.format(
                cyan('[{}]'.format(i)),
                bright(", ".join(sorted(e['participants'].keys()))),
                cyan(" ({})".format(e['totalMessagesSent'])))
            )
            max_participant_length = max(len(k) for k in e['participants'])

            stream.write("     Oldest message:\n")
            stream.write("       - Date:    {}\n".format(e['oldestMessage']['date']))
            stream.write("       - Sender:  {}\n".format(e['oldestMessage']['sender']))
            stream.write("       - Content: {}\n".format(e['oldestMessage']['message']))
            stream.write("     Newest message:\n")
            stream.write("       - Date:    {}\n".format(e['newestMessage']['date']))
            stream.write("       - Sender:  {}\n".format(e['newestMessage']['sender']))
            stream.write("       - Content: {}\n".format(e['newestMessage']['message']))
            stream.write("     Participants:\n")
            for k, v in sorted(e['participants'].items(), key=lambda p: -p[1]['messagesSent']):
                stream.write("      - {} {}\n".format(
                    k.ljust(max_participant_length),
                    green('[{}|{}%]'.format(v['messagesSent'], v['percentOfThread']))
                ))
                stream.write('        > Most common words: {}\n'.format(
                    ', '.join(v['mostCommonWords'])))
            stream.write('\n')

    def write_json(self, stream, pretty=False):
        stream.write(json.dumps(
            self.compute_stats(), ensure_ascii=False, indent=4 if pretty else None))
        stream.write('\n')

    def write_yaml(self, stream):
        data = yaml.safe_dump(
            self.compute_stats(), default_flow_style=False, allow_unicode=True)
        if six.PY2:
            data = data.decode('utf8')
        stream.write(data)
        stream.write('\n')

