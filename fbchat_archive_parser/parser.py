from __future__ import unicode_literals
import re

from collections import defaultdict
import hashlib
from io import open
import sys
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import XMLParser

from . import (ChatThread, ChatMessage, FacebookChatHistory)
from .utils import yellow, magenta
from .time import parse_timestamp


class SafeXMLFile(object):
    """
    Let's implement our own stream filter to remove the inexplicably present
    control characters for us. We will analyze the incoming byte stream and
    remove any instances of the offending characters.
    """

    def __init__(self, stream):

        # Create a regex for matching all illegal characters within the
        # XML 1.1 spec so that we can filter them out.
        illegal_unichrs = [(0x00, 0x08), (0x0B, 0x0C), (0x0E, 0x1F),
                           (0x7F, 0x84), (0x86, 0x9F), (0xFDD0, 0xFDDF),
                           (0xFFFE, 0xFFFF)]
        if sys.maxunicode >= 0x10000:  # not narrow build
            illegal_unichrs.extend([(0x1FFFE, 0x1FFFF), (0x2FFFE, 0x2FFFF),
                                    (0x3FFFE, 0x3FFFF), (0x4FFFE, 0x4FFFF),
                                    (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF),
                                    (0x7FFFE, 0x7FFFF), (0x8FFFE, 0x8FFFF),
                                    (0x9FFFE, 0x9FFFF), (0xAFFFE, 0xAFFFF),
                                    (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF),
                                    (0xDFFFE, 0xDFFFF), (0xEFFFE, 0xEFFFF),
                                    (0xFFFFE, 0xFFFFF), (0x10FFFE, 0x10FFFF)])
        uni = chr if sys.version_info >= (3, 0) else unichr
        illegal_ranges = ["%s-%s" % (uni(low), uni(high))
                          for (low, high) in illegal_unichrs]
        self.scrubber = re.compile('[%s]' % ''.join(illegal_ranges))
        self.stream = stream

    def __enter__(self):
        # Read the stream in at the character boundaries to ensure we are not
        # accidentally extracting only partial characters in our buffers.
        self.open_file = open(self.stream, 'rt', encoding='utf-8')
        return self

    def __exit__(self, *args):
        self.open_file.close()

    def read(self, size=-1):
        buff = self.open_file.read(size)
        # The XML parser is dumb and seems to only utilize UTF-8
        # encoders/decoders if we hand it a byte stream. Fortunately, it
        # doesn't seem to care if it got more or less bytes then it asked for.
        return re.sub(self.scrubber, '', buff).encode('utf-8')


class MessageHtmlParser(object):

    def __init__(self, path, timezone_hints=None, use_utc=True,
                 progress_output=False, filter=None):

        self.chat_threads = dict()
        self.message_cache = None
        self.user = None

        self.current_thread = None
        self.current_sender = None
        self.current_timestamp = None
        self.last_line_len = 0

        self.path = path
        self.progress_output = progress_output
        self.filter = tuple(p.lower() for p in filter) if filter else None
        self.seq_num = 0
        self.wait_for_next_thread = False
        self.thread_signatures = set()
        self.timezone_hints = {}
        self.use_utc = use_utc
        if timezone_hints:
            self.timezone_hints = timezone_hints

    def parse(self):
        self._parse_content()
        return FacebookChatHistory(self.user, self.chat_threads)

    def _clear_output(self):
        """
        Clears progress output (if any) that was written to the screen.
        """
        # If progress output was being written, clear it from the screen.
        if self.progress_output:
            sys.stderr.write("\r".ljust(self.last_line_len))
            sys.stderr.write("\r")
            sys.stderr.flush()

    def _parse_content(self):
        """
        Parses the HTML content as a stream. This is far less memory
        intensive than loading the entire HTML file into memory, like
        BeautifulSoup does.
        """

        # Cast to str to ensure not unicode under Python 2, as the parser
        # doesn't like that.
        parser = XMLParser(encoding=str('UTF-8'))
        with SafeXMLFile(self.path) as f:
            for pos, element in ET.iterparse(f, events=("start", "end"),
                                             parser=parser):
                self._process_element(pos, element)

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
        if not self.filter:
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
                        line = "\rContinuing chat thread with %s %s..." \
                               % (yellow(participants_text),
                                  magenta("<@%d messages>"
                                          % len(self.current_thread)))
                    else:
                        line = "\rDiscovered chat thread with %s..." \
                                % yellow(participants_text)
                        self.current_thread = ChatThread(participants)
                if self.progress_output:
                    sys.stderr.write(line.ljust(self.last_line_len))
                    sys.stderr.flush()
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
                self.current_timestamp =\
                    parse_timestamp(e.text, self.use_utc, self.timezone_hints)
        elif tag == "p" and pos == "end":
            if not self.current_sender or not self.current_timestamp:
                raise Exception("Data missing from message. This is a parsing"
                                "error: %s, %s" % (self.current_timestamp,
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
            if not self.user:
                self.user = e.text.strip()
