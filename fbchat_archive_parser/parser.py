import xml.etree.ElementTree as ET
from io import open
from datetime import datetime
from threading import Thread
import sys
from sortedcontainers import SortedList

class ChatMessage(object):

    def __init__(self, timestamp, sender, content):
        self.sender = sender
        self.timestamp = timestamp
        self.content = content

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def __len__(self):
        return len(self.content)

class ChatThread(object):

    def __init__(self, participants):
        self.participants = list(participants)
        self.participants.sort()
        self.messages = SortedList()#sortedlist()

    def add_message(self, message):
        self.messages.add(message)

    def __lt__(self, other):
        return len(self.messages) < len(other.messages)

    def __len__(self):
        return len(self.messages)

class FacebookChatHistory:

    _DATE_FORMAT = "%A, %B %d, %Y at %I:%M%p %z"

    def __init__(self, stream, callback=None, progress_output=False):

        self.chat_threads = dict()
        self.user = None

        if callback:
            if not callable(callback):
                raise Exception("Callback must be callable")
            thread = Thread(target=self.__parse_content, args=(stream, callback, progress_output))
            thread.start()
        else:
            self.__parse_content(stream, callback, progress_output)

    def __parse_content(self, stream, callback=None, progress_output=False):

        current_thread = None
        current_sender = None
        current_timestamp = None
        last_line_len = 0

        dom_tree = ET.iterparse(stream, events=("start", "end"))

        try:
            while (True):
                pos, e = next(dom_tree)
                if e.tag not in ("div", "span", "p", "h1"):
                    continue

                class_attr = e.attrib.get('class', [])

                if e.tag == "div":
                    if "thread" in class_attr and pos == "start":
                        participants_text = e.text
                        participants = e.text
                        participants = participants.split(", ")
                        participants.sort()
                        if self.user in participants:
                            participants.remove(self.user)
                        participants = tuple(participants)
                        if len(participants) > 4:
                            participants_text = participants_text[0:30] \
                                + "... <%s>" % str(len(participants))
                        if participants in self.chat_threads:
                            current_thread = self.chat_threads[participants]
                            line = "\rContinuing chat thread with [{}]<@{} messages>..." \
                                        .format(participants_text, len(current_thread))
                        else:
                            line = "\rDiscovered chat thread with [{}]..." \
                                        .format(participants_text)
                            current_thread = ChatThread(participants)
                            self.chat_threads[participants] = current_thread
                        if progress_output:
                            sys.stderr.write(line.ljust(last_line_len))
                        last_line_len = len(line)

                        self.chat_threads[participants] = current_thread

                elif e.tag == "span" and pos == "end":

                    if "user" in class_attr:
                        current_sender = e.text
                    elif "meta" in class_attr:
                        current_timestamp = e.text
                        if "PDT" in current_timestamp:
                            current_timestamp = current_timestamp.replace("PDT", "-0700")
                        elif "PST" in current_timestamp:
                            current_timestamp = current_timestamp.replace("PST", "-0800")
                        else:
                            raise Exception("Expected only PST/PDT timezones (found %s). This is a bug."
                                % current_timestamp)
                        current_timestamp = datetime.strptime(current_timestamp, self._DATE_FORMAT)

                elif e.tag == "p" and pos == "end":
                    if current_sender is None or current_timestamp is None:
                        raise Exception("Data missing from message. This is a parsing error: %s, %s"
                            % (current_timestamp, current_sender))
                    current_thread.add_message(ChatMessage(current_timestamp, current_sender, e.text))
                    current_sender, current_timestamp = None, None

                elif e.tag == "h1" and pos == "end":
                    if self.user == None:
                        self.user = e.text.strip()

        except StopIteration:
            pass

        if progress_output:
            sys.stderr.write("\r".ljust(last_line_len))
            sys.stderr.write("\r")

        if callback:
            callback(self)
