from __future__ import unicode_literals

import sys
import xml.etree.ElementTree as ET
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
ChatMessage = namedtuple('ChatMessage',
                         ['timestamp', 'seq_num', 'sender', 'content'])


class ChatThread(object):

    def __init__(self, participants):
        self.participants = list(participants)
        self.participants.sort()
        self.messages = SortedList()

    def add_message(self, message):
        self.messages.add(message)

    def __lt__(self, other):
        return len(self.messages) < len(other.messages)

    def __len__(self):
        return len(self.messages)


class FacebookChatHistory:

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
        self.callback = callback
        self.filter = set(p.lower() for p in filter) if filter else None
        self.seq_num = 0
        self.wait_for_next_thread = False
        self.thread_signatures = set()

        self.__parse_content()

    def __parse_content(self):

        for pos, element in ET.iterparse(self.stream, events=("start", "end")):
            self.__process_element(pos, element)

        if self.progress_output:
            sys.stdout.write("\r".ljust(self.last_line_len))
            sys.stdout.write("\r")
            sys.stdout.flush()

        sys.stdout.write(Style.RESET_ALL)
        sys.stdout.write(Fore.RESET)
        sys.stdout.write(Back.RESET)

        if self.callback:
            self.callback(self)

    def __should_record_thread(self, participants):
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

        class_attr = e.attrib.get('class', [])

        if e.tag == "div" and "thread" in class_attr:
            if pos == "start":
                self.message_cache = []
                self.current_signature = hashlib.md5()
                participants_text = e.text.strip()
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
                if self.wait_for_next_thread:
                    line = ("\rSkipping chat thread with {}" +
                            Fore.MAGENTA + "..." +
                            Fore.WHITE).format(participants_text)
                else:
                    if participants in self.chat_threads:
                        self.current_thread = self.chat_threads[participants]
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
                self.current_signature = self.current_signature.hexdigest()
                if self.current_signature in self.thread_signatures:
                    sys.stderr.write("Duplicate thread detected: %s\n "
                                     % str(self.current_thread.participants))
                    return
                self.thread_signatures.add(self.current_signature)
                for cm in self.message_cache:
                    self.current_thread.add_message(cm)
                participants = ", ".join(self.current_thread.participants)
                self.chat_threads[participants] = self.current_thread
        elif self.wait_for_next_thread:
            return
        elif e.tag == "span" and pos == "end":

            if "user" in class_attr:
                self.current_sender = e.text
            elif "meta" in class_attr:
                self.current_timestamp = e.text
                if "PDT" in self.current_timestamp:
                    self.current_timestamp = \
                        self.current_timestamp.replace(" PDT", "")
                    delta = timedelta(hours=-7)
                elif "PST" in self.current_timestamp:
                    self.current_timestamp = \
                        self.current_timestamp.replace(" PST", "")
                    delta = timedelta(hours=-8)
                else:
                    raise UnexpectedTimeZoneError(
                        "Expected only PST/PDT timezones (found %s). This "
                        "is a bug." % self.current_timestamp)
                self.current_timestamp = datetime.strptime(
                                                  self.current_timestamp,
                                                  self.__DATE_FORMAT)
                self.current_timestamp += delta
                self.current_timestamp = \
                    self.current_timestamp.replace(tzinfo=pytz.utc)

        elif e.tag == "p" and pos == "end":
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

        elif e.tag == "h1" and pos == "end":
            if self.user is None:
                self.user = e.text.strip()
