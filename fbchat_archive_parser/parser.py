import xml.etree.ElementTree as ET
from io import open
from datetime import datetime
from threading import Thread
import sys
from sortedcontainers import SortedList

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
        return self.timestamp < other.timestamp \
                or self._seq_num > other._seq_num

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

    _DATE_FORMAT = "%A, %B %d, %Y at %I:%M%p"

    def __init__(self, stream, callback=None, progress_output=False):

        self.chat_threads = dict()
        self.user = None

        self.current_thread = None
        self.current_sender = None
        self.current_timestamp = None
        self.caching_timestamp = None
        self.last_line_len = 0

        self.stream = stream
        self.progress_output = True
        self.callback = callback
        self.seq_num = 0

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
            sys.stderr.write("\r".ljust(self.last_line_len))
            sys.stderr.write("\r")

        if self.callback:
            self.callback(self)

    def __process_element(self, pos, e):

        if e.tag not in ("div", "span", "p", "h1"):
            return

        class_attr = e.attrib.get('class', [])

        if e.tag == "div":
            if "thread" in class_attr and pos == "start":
                participants_text = e.text.strip()
                participants = participants_text.split(", ")
                participants.sort()
                if self.user in participants:
                    participants.remove(self.user)
                participants = tuple(participants)
                if len(participants) > 4:
                    participants_text = participants_text[0:30] \
                        + "... <%s>" % str(len(participants))
                if participants in self.chat_threads:
                    self.current_thread = self.chat_threads[participants]
                    line = "\rContinuing chat thread with [{}]<@{} messages>..." \
                                .format(participants_text, len(self.current_thread))
                else:
                    line = "\rDiscovered chat thread with [{}]..." \
                                .format(participants_text)
                    self.current_thread = ChatThread(participants)
                    self.chat_threads[participants] = self.current_thread
                if self.progress_output:
                    sys.stderr.write(line.ljust(self.last_line_len))
                self.last_line_len = len(line)

                self.chat_threads[participants] = self.current_thread

        elif e.tag == "span" and pos == "end":

            if "user" in class_attr:
                self.current_sender = e.text
            elif "meta" in class_attr:
                self.current_timestamp = e.text
                if "PDT" in self.current_timestamp:
                    self.current_timestamp = self.current_timestamp.replace("PDT", "") #-7
                    delta = timedelta(hours=-7)
                elif "PST" in self.current_timestamp:
                    self.current_timestamp = self.current_timestamp.replace("PST", "") #-8
                    delta = timedelta(hours=-8)
                else:
                    raise UnexpectedTimeZoneError("Expected only PST/PDT timezones (found %s). This is a bug."
                        % self.current_timestamp)
                self.current_timestamp = datetime.strptime(self.current_timestamp, self._DATE_FORMAT)
                self.current_timestamp += delta
                self.current_timestamp = self.current_timestamp.replace(tzinfo=pytz.utc)

        elif e.tag == "p" and pos == "end":
            if self.current_sender is None or self.current_timestamp is None:
                raise Exception("Data missing from message. This is a parsing error: %s, %s"
                    % (self.current_timestamp, self.current_sender))

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
            if self.user == None:
                self.user = e.text.strip()

