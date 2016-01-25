from __future__ import unicode_literals

import sys
import xml.etree.ElementTree as ET
import pytz

from io import open
from datetime import datetime, timedelta
from threading import Thread
from sortedcontainers import SortedList
from colorama import Fore, Back, Style


class UnexpectedTimeZoneError(Exception):
    pass


class ChatMessage(object):

    def __init__(self, timestamp, sender, content, seq_num):
        self.sender = sender
        self.timestamp = timestamp
        self.content = content
        self._seq_num = seq_num

    def __lt__(self, other):
        # More recent messages have a lower sequence number.
        return self.timestamp < other.timestamp or \
                (self.timestamp == other.timestamp and
                 self._seq_num > other._seq_num)

    def __len__(self):
        return len(self.content)


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

    def __init__(self, stream, callback=None, progress_output=False,
                 filter=None):

        self.chat_threads = dict()
        self.user = None

        self.current_thread = None
        self.current_sender = None
        self.current_timestamp = None
        self.caching_timestamp = None
        self.last_line_len = 0

        self.stream = stream
        self.progress_output = progress_output
        self.callback = callback
        self.filter = set(p.lower() for p in filter) if filter else None
        self.seq_num = 0
        self.wait_for_next_thread = False

        if callback:
            if not callable(callback):
                raise Exception("Callback must be callable")
            thread = Thread(target=self.__parse_content)
            thread.start()
        else:
            self.__parse_content()

    def __parse_content(self):

        dom_tree = ET.iterparse(self.stream, events=("start", "end"))

        try:
            while (True):
                pos, e = next(dom_tree)
                self.__process_element(pos, e)

        except StopIteration:
            pass

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
        p_lower = tuple(p.lower() for p in participants)
        for t_p in (set(p_lower), set(" ".join(p_lower).split(" "))):
            f_p = set(self.filter)
            for p in t_p:
                f_p.discard(p)
            if len(f_p) == 0:
                return True
        return False

    def __process_element(self, pos, e):

        class_attr = e.attrib.get('class', [])

        if e.tag == "div":
            if "thread" in class_attr and pos == "start":
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
                        self.chat_threads[participants] = self.current_thread
                if self.progress_output:
                    sys.stdout.write(line.ljust(self.last_line_len))
                    sys.stdout.flush()
                self.last_line_len = len(line)

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

            self.current_thread.add_message(
                ChatMessage(
                    self.current_timestamp,
                    self.current_sender,
                    e.text.strip() if e.text else "",
                    self.seq_num
                )
            )

            self.seq_num += 1

            self.current_sender, self.current_timestamp = None, None

        elif e.tag == "h1" and pos == "end":
            if self.user is None:
                self.user = e.text.strip()
