from __future__ import unicode_literals

import sys
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import XMLParser
import pytz
import hashlib

from io import open
from datetime import datetime, timedelta
from sortedcontainers import SortedList
from colorama import Fore, Back, Style

from collections import namedtuple, defaultdict


class UnexpectedTimeZoneError(Exception):
    pass

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
    __DATE_FORMAT = "%A, %B %d, %Y at %I:%M%p"

    def __init__(self, stream, progress_output=False, filter=None):

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

        self.__parse_content()

    def _clear_output(self):
        """
        Clears progress output (if any) that was written to the screen.
        """
        # If progress output was being written, clear it from the screen.
        if self.progress_output:
            sys.stdout.write("\r".ljust(self.last_line_len))
            sys.stdout.write("\r")
            sys.stdout.write(Style.RESET_ALL)
            sys.stdout.write(Fore.RESET)
            sys.stdout.write(Back.RESET)
            sys.stdout.flush()

    def __parse_content(self):
        """
        Parses the HTML content as a stream. This is far less memory
        intensive than loading the entire HTML file into memory, like
        BeautifulSoup does.
        """
        try:
            for pos, element in ET.iterparse(
                    self.stream, events=("start", "end"),
                    parser=XMLParser(encoding=str('UTF-8'))):
                self.__process_element(pos, element)
        except ET.ParseError:
            # Although apparently uncommon, some users have message logs that
            # may not conform to strict XML standards. We will fall back to
            # the BeautifulSoup parser in that case.

            # Purge all collected data.
            self.chat_threads = dict()
            self.thread_signatures = set()
            self.message_cache = None
            self.user = None

            self._clear_output()
            sys.stderr.write('The streaming parser crashed due to malformed '
                             'XML. Falling back to the less strict/efficient '
                             'BeautifulSoup parser. This may take a while... '
                             '\n')
            sys.stderr.flush()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(open(self.stream, 'r').read(), 'lxml')
            self.__process_element('end', soup.find('h1'))
            for thread_element in soup.find_all('div', class_='thread'):
                self.__process_element('start', thread_element)
                for e in thread_element:
                    if e.name == 'div':
                        user = e.find('span', class_='user')
                        meta = e.find('span', class_='meta')
                        self.__process_element('end', user)
                        self.__process_element('end', meta)
                    elif e.name == 'p':
                        self.__process_element('end', e)
                self.__process_element('end', thread_element)

        self._clear_output()

    def __should_record_thread(self, participants):
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

    def __process_element(self, pos, e):
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
                        not self.__should_record_thread(participants)
                    if len(participants) > 4:
                        participants_text = participants_text[0:30] \
                            + "... <%s>" % str(len(participants))
                    participants_text = Fore.YELLOW + '[' + \
                        participants_text + ']' + Fore.WHITE
                else:
                    participants_text = "unknown participants"
                    self.wait_for_next_thread = True
                if self.wait_for_next_thread:
                    line = ("\rSkipping chat thread with {}" +
                            Fore.MAGENTA + "..." +
                            Fore.WHITE).format(participants_text)
                else:
                    participants_key = ", ".join(participants)
                    if participants_key in self.chat_threads:
                        self.current_thread =\
                            self.chat_threads[participants_key]
                        line = ("\rContinuing chat thread with {}" +
                                Fore.MAGENTA + "<@{} messages>..." +
                                Fore.WHITE).format(participants_text,
                                                   len(self.current_thread))
                    else:
                        line = "\rDiscovered chat thread with {}..." \
                                    .format(participants_text)
                        self.current_thread = ChatThread(participants)
                if self.progress_output:
                    sys.stdout.write(line.ljust(self.last_line_len))
                    sys.stdout.flush()
                self.last_line_len = len(line)
            elif pos == "end" and not self.wait_for_next_thread:
                # Facebook has a tendency to return the same thread more than
                # once during history collection. Check the collective hash of
                # all messages in the thread to ensure that we have already
                # recorded it.
                self.current_signature = self.current_signature.hexdigest()
                if self.current_signature in self.thread_signatures:
                    # FIXME: Suppressed until use of a logging library is
                    #       implemented
                    # sys.stderr.write("Duplicate thread detected: %s\n "
                    #                 % str(self.current_thread.participants))
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
                self.current_timestamp = e.text
                if "PDT" in self.current_timestamp:
                    self.current_timestamp =\
                        self.current_timestamp.replace(" PDT", "")
                    delta = timedelta(hours=-7)
                elif "PST" in self.current_timestamp:
                    self.current_timestamp =\
                        self.current_timestamp.replace(" PST", "")
                    delta = timedelta(hours=-8)
                elif "UTC+" in self.current_timestamp or\
                     "UTC-" in self.current_timestamp:
                    self.current_timestamp, offset =\
                        self.current_timestamp.split(" UTC")
                    offset = [int(x) for x in offset[1:].split(':')]
                    if '+' in self.current_timestamp:
                        delta = timedelta(hours=offset[0], minutes=offset[1])
                    else:
                        delta = timedelta(hours=-1 * offset[0],
                                          minutes=-1 * offset[1])
                else:
                    raise UnexpectedTimeZoneError(
                        "Unexpected timezone format (found %s). Please "
                        "report this bug." % self.current_timestamp)
                self.current_timestamp = datetime.strptime(
                                                  self.current_timestamp,
                                                  self.__DATE_FORMAT)
                self.current_timestamp += delta
                self.current_timestamp = \
                    self.current_timestamp.replace(tzinfo=pytz.utc)

        elif tag == "p" and pos == "end":
            if self.current_sender is None or self.current_timestamp is None:
                raise Exception("Data missing from message. This is a parsing"
                                "error: %s, %s"
                                % (self.current_timestamp,
                                   self.current_sender))

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
            if self.user is None:
                self.user = e.text.strip()
