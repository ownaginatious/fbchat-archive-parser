from __future__ import unicode_literals

from collections import namedtuple, defaultdict
from datetime import datetime, timedelta
import hashlib
from io import open
import sys
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import XMLParser

from sortedcontainers import SortedList
import pytz
from pytz import all_timezones, timezone

from .utils import error, yellow, magenta


TIMEZONE_MAP = defaultdict(lambda: defaultdict(set))
for tz_name in all_timezones:
    for dst in (True, False):
        tz = timezone(tz_name).localize(datetime.now(), is_dst=dst)
        offset_raw = tz.strftime("%z")
        if offset_raw[0] == '-':
            offset = (-1 * int(offset_raw[1:3]), -1 * int(offset_raw[3:5]))
        else:
            offset = (int(offset_raw[1:3]), int(offset_raw[3:5]))
        offset += (offset_raw,)
        TIMEZONE_MAP[tz.strftime("%Z")][offset].add(tz_name)


class UnexpectedTimeZoneError(Exception):
    pass


class AmbiguousTimeZoneError(Exception):

    def __init__(self, tz_name, tz_options):
        self.tz_name = tz_name
        self.tz_options = tz_options
        super(AmbiguousTimeZoneError, self).__init__()


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

    def __lt__(self, other):
        return len(self.messages) < len(other.messages)

    def __len__(self):
        return len(self.messages)


class FacebookChatHistory:
    """
    Represents the Facebook chat history between the owner of
    the history and their contacts.

    """
    _DATE_FORMAT = "%A, %B %d, %Y at %I:%M%p"

    def __init__(self, stream, timezone_hints=None, progress_output=False,
                 filter=None, bs4=False):

        self.chat_threads = dict()
        self.message_cache = None
        self.user = None

        self.current_thread = None
        self.current_sender = None
        self.current_timestamp = None
        self.last_line_len = 0

        self.stream = stream
        self.progress_output = progress_output
        self.filter = set(p.lower() for p in filter) if filter else None
        self.seq_num = 0
        self.wait_for_next_thread = False
        self.thread_signatures = set()
        self.timezone_hints = {}
        if timezone_hints:
            self.timezone_hints = timezone_hints
        self._parse_content(bs4)

    def _clear_output(self):
        """
        Clears progress output (if any) that was written to the screen.
        """
        # If progress output was being written, clear it from the screen.
        if self.progress_output:
            sys.stdout.write("\r".ljust(self.last_line_len))
            sys.stdout.write("\r")
            sys.stdout.flush()

    def _parse_content(self, use_bs4):
        """
        Parses the HTML content as a stream. This is far less memory
        intensive than loading the entire HTML file into memory, like
        BeautifulSoup does.
        """
        if not use_bs4:
            for pos, element in ET.iterparse(
                    self.stream, events=("start", "end"),
                    parser=XMLParser(encoding=str('UTF-8'))):
                self._process_element(pos, element)
        else:
            # Although apparently uncommon, some users have message logs that
            # may not conform to strict XML standards. We will fall back to
            # the BeautifulSoup parser in that case.
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(open(self.stream, 'r').read(), 'html.parser')
            self._process_element('end', soup.find('h1'))
            for thread_element in soup.find_all('div', class_='thread'):
                self._process_element('start', thread_element)
                for e in thread_element:
                    if e.name == 'div':
                        user = e.find('span', class_='user')
                        meta = e.find('span', class_='meta')
                        self._process_element('end', user)
                        self._process_element('end', meta)
                    elif e.name == 'p':
                        self._process_element('end', e)
                self._process_element('end', thread_element)

        self._clear_output()

    def _should_record_thread(self, participants):
        """
        Determines if the thread should be parsed based on the
        participants and the filter given.

        For example, if the filter states ['jack', 'billy joe'],
        then only threads with exactly two participants
        (excluding the owner of the chat history) containing
        someone with the first or last name 'Jack' and someone
        named 'Billy Joel' will be included.

        Any of the following would match that criteria:

            - Jack Stevenson, Billy Joel
            - Billy Joel, Jack Stevens
            - Jack Jenson, Billy Joel
            - Jack Jack, Billy Joel

        participants -- the participants of the thread
                        (excluding the history owner)
        """
        if self.filter is None:
            return True
        if len(participants) != len(self.filter):
            return False
        participants = [[p.lower()] + p.lower().split(" ")
                        for p in participants]
        matches = defaultdict(set)
        for e, p in enumerate(participants):
            for f in self.filter:
                if f in p:
                    matches[f].add(e)
        matched = set()
        for f in matches:
            if len(matches[f]) == 0:
                return False
            matched |= matches[f]
        return len(matched) == len(participants)

    def _parse_time(self, time_element):
        """
        Facebook is highly inconsistent with their timezone formatting.
        Sometimes it's in UTC+/-HH:MM form, and other times its in the
        ambiguous PST, PDT. etc format.

        We have to handle the ambiguity by asking for cues from the user.

        time_element -- The time element to parse and convert to UTC.
        """
        raw_timestamp = time_element.text
        timestamp, offset = raw_timestamp.rsplit(" ", 1)
        if "UTC+" in offset or "UTC-" in offset:
            if offset[3] == '-':
                offset = [-1 * int(x) for x in offset[4:].split(':')]
            else:
                offset = [int(x) for x in offset[4:].split(':')]
        else:
            offset_hint = self.timezone_hints.get(offset, None)
            if not offset_hint:
                if offset not in TIMEZONE_MAP:
                    raise UnexpectedTimeZoneError(raw_timestamp)
                elif len(TIMEZONE_MAP[offset]) > 1:
                    raise AmbiguousTimeZoneError(offset, TIMEZONE_MAP[offset])
                offset = list(TIMEZONE_MAP[offset].keys())[0][:2]
            else:
                offset = offset_hint

        if len(offset) == 1:
            # Timezones without minute offset may be formatted
            # as UTC+X (e.g UTC+8)
            offset += [0]

        delta = timedelta(hours=offset[0], minutes=offset[1])

        timestamp = datetime.strptime(timestamp, self._DATE_FORMAT)
        timestamp += delta
        self.current_timestamp = timestamp.replace(tzinfo=pytz.utc)

    def _process_element(self, pos, e):
        """
        Parses an incoming HTML element/node for data.

        pos -- the part of the element being parsed
               (start/end)
        e   -- the element being parsed
        """
        class_attr = e.attrib.get('class', [])\
            if e.attrib else e.get('class', [])
        tag = e.tag if e.tag else e.name
        if tag == "div" and "thread" in class_attr:
            if pos == "start":
                self.message_cache = []
                self.current_signature = hashlib.md5()
                # Very rarely threads may lack information on who the
                # participants are. We will consider those threads corrupted
                # and skip them.
                if e.text:
                    participants_text = e.text.strip()\
                                        if e.attrib else e.contents[0].strip()
                    participants = participants_text.split(", ")
                    participants.sort()
                    if self.user in participants:
                        participants.remove(self.user)
                    participants = tuple(participants)
                    self.wait_for_next_thread = \
                        not self._should_record_thread(participants)
                    if len(participants) > 4:
                        participants_text = participants_text[0:30] \
                            + "... <%s>" % str(len(participants))
                    participants_text = yellow("[%s]" % participants_text)
                else:
                    participants_text = "unknown participants"
                    self.wait_for_next_thread = True
                if self.wait_for_next_thread:
                    line = "\rSkipping chat thread with %s..." % \
                            yellow(participants_text)
                else:
                    participants_key = ", ".join(participants)
                    if participants_key in self.chat_threads:
                        self.current_thread =\
                            self.chat_threads[participants_key]
                        line = "\rContinuing chat thread with %s %s..." % (
                               yellow(participants_text),
                               magenta("<@%d messages>" % len(self.current_thread)))
                    else:
                        line = "\rDiscovered chat thread with %s..." \
                                % yellow(participants_text)
                        self.current_thread = ChatThread(participants)
                if self.progress_output:
                    sys.stdout.write(line.ljust(self.last_line_len))
                    sys.stdout.flush()
                self.last_line_len = len(line)
            elif pos == "end" and not self.wait_for_next_thread:
                # Facebook has a tendency to return the same thread more than
                # once during history collection. Check the collective hash of
                # all messages in the thread to ensure that we have not already
                # recorded it.
                self.current_signature = self.current_signature.hexdigest()
                if self.current_signature in self.thread_signatures:
                    # FIXME: Suppressed until use of a logging library is
                    #        implemented
                    # error("Duplicate thread detected: %s\n "
                    #        % str(self.current_thread.participants))
                    return
                # Mark it as a signature as seen.
                self.thread_signatures.add(self.current_signature)
                for cm in self.message_cache:
                    self.current_thread.add_message(cm)
                participants = ", ".join(self.current_thread.participants)
                self.chat_threads[participants] = self.current_thread
        elif self.wait_for_next_thread:
            return
        elif tag == "span" and pos == "end":
            if "user" in class_attr:
                self.current_sender = e.text
            elif "meta" in class_attr:
                self._parse_time(e)
        elif tag == "p" and pos == "end":
            if not self.current_sender or not self.current_timestamp:
                raise Exception("Data missing from message. This is a parsing"
                                "error: %s, %s" % (self.current_timestamp,
                                                   self.current_sender)
                      )
            cm = ChatMessage(timestamp=self.current_timestamp,
                             sender=self.current_sender,
                             content=e.text.strip() if e.text else "",
                             seq_num=self.seq_num)
            self.message_cache += [cm]
            self.current_signature.update(str(cm.timestamp).encode('utf-8'))
            self.current_signature.update(cm.sender.encode('utf-8'))
            self.current_signature.update(cm.content.encode('utf-8'))

            self.seq_num -= 1
            self.current_sender, self.current_timestamp = None, None

        elif tag == "h1" and pos == "end":
            if not self.user:
                self.user = e.text.strip()
