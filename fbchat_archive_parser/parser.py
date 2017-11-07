from __future__ import unicode_literals

from collections import defaultdict
import io
import os
import platform
import re
import sys
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import XMLParser

import six

from . import (ChatThread, ChatMessage, FacebookChatHistory)
from .name_resolver import DummyNameResolver
from .utils import yellow, magenta
from .time import parse_timestamp


class UnsuitableParserError(Exception):
    pass


class MissingReferenceError(Exception):
    pass


if six.PY2:
    FileNotFoundError = OSError


class SafeXMLStream(object):
    """
    Let's implement our own stream filter to remove the inexplicably present
    control characters for us. We will analyze the incoming byte stream and
    remove any instances of the offending characters.
    """

    # The XML parser is super basic and can't understand special HTML-specific
    # aliases like &nbsp;. This header is artificially prepended to each XML
    # stream to tell guide the parser on what the token signifies.
    HTML_ENTITY_DEF = b"<!DOCTYPE html [<!ENTITY nbsp ' '>]>"

    def __init__(self, stream):

        # Create a regex for matching all illegal characters within the
        # XML 1.1 spec so that we can filter them out.
        illegal_unichrs = [(0x00, 0x08), (0x0B, 0x0C), (0x0E, 0x1F),
                           (0x7F, 0x84), (0x86, 0x9F), (0xFDD0, 0xFDDF),
                           (0xFFFE, 0xFFFF), (0xD800, 0xDFFF),
                           (0x0B, 0x1F)]
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
        self.returned_dtd = False

    def read(self, size=-1):

        if not self.returned_dtd:
            self.returned_dtd = True
            return self.HTML_ENTITY_DEF

        buff = self.stream.read(size)
        # The XML parser is dumb and seems to only utilize UTF-8
        # encoders/decoders if we hand it a byte stream. Fortunately, it
        # doesn't seem to care if it got more or less bytes then it asked for.
        return re.sub(self.scrubber, '', buff).encode('utf-8')


def _truncate(string, length=60):
    if len(string) > 60:
        return "%s..." % string[:length]
    return string


def _tag_and_class_attr(element):
    if element.attrib:
        class_attr = element.attrib.get('class', [])
    else:
        class_attr = element.get('class', [])
    tag = element.tag if element.tag else element.name
    return tag, class_attr


class ChatThreadParser(object):

    def __init__(self, element_iter, timezone_hints=None, use_utc=True, name_resolver=None,
                 no_sender_warning_status=True, seq_num=0):

        self.name_resolver = name_resolver or DummyNameResolver()

        self.messages = None
        self.current_sender = None
        self.current_timestamp = None

        self.element_iter = element_iter
        self.seq_num = seq_num
        self.timezone_hints = timezone_hints or {}
        self.use_utc = use_utc
        self.no_sender_warning_status = no_sender_warning_status
        self.messages = []

    def parse(self, participants):
        self.messages = []
        self.current_sender = None
        self.current_timestamp = None

        for pos, element in self.element_iter:
            finished = self._process_element(pos, element)
            if finished:
                break

        thread = ChatThread(participants)
        for m in self.messages:
            thread.add_message(m)
        return self.no_sender_warning_status, thread

    def skip(self):
        """
        Eats through the input iterator without recording the content.
        """
        for pos, element in self.element_iter:
            tag, class_attr = _tag_and_class_attr(element)
            if tag == "div" and "thread" in class_attr and pos == "end":
                break

    def _process_element(self, pos, e):
        """
        Parses an incoming HTML element/node for data.

        pos -- the part of the element being parsed
               (start/end)
        e   -- the element being parsed
        """
        tag, class_attr = _tag_and_class_attr(e)

        if tag == "div" and "thread" in class_attr and pos == "end":
            return True
        elif tag == "span" and pos == "end":
            if "user" in class_attr:
                self.current_sender = self.name_resolver.resolve(e.text)
            elif "meta" in class_attr:
                self.current_timestamp =\
                    parse_timestamp(e.text, self.use_utc, self.timezone_hints)
        elif tag == "p" and pos == "end":
            if not self.current_timestamp:
                # This is the typical error when the new Facebook format is
                # used with the legacy parser.
                raise UnsuitableParserError
            if not self.current_sender:
                if not self.no_sender_warning_status:
                    sys.stderr.write(
                        "\rWARNING: The sender was missing in one or more parsed messages. "
                        "This is an error on Facebook's end that unfortunately cannot be "
                        "recovered from. Some or all messages in the output may show the "
                        "sender as 'Unknown' within each thread.\n")
                    self.no_sender_warning = True
                self.current_sender = "Unknown"

            cm = ChatMessage(timestamp=self.current_timestamp,
                             sender=self.current_sender,
                             content=e.text.strip() if e.text else "",
                             seq_num=self.seq_num)
            self.messages += [cm]

            self.seq_num -= 1
            self.current_sender, self.current_timestamp = None, None

        return False


class MessageHtmlParser(object):

    def __init__(self, handle, timezone_hints=None, use_utc=True,
                 progress_output=False, thread_filter=None, name_resolver=None):

        self.name_resolver = name_resolver or DummyNameResolver()

        self.chat_threads = dict()
        self.message_cache = None
        self.user = None

        self.last_line_len = 0

        self.handle = SafeXMLStream(handle)
        self.progress_output = progress_output
        self.thread_filter = (
            tuple(p.lower() for p in thread_filter) if thread_filter else None)
        self.seq_num = 0
        self.thread_signatures = set()
        self.timezone_hints = timezone_hints or {}
        self.use_utc = use_utc
        self.no_sender_warning = False

    def should_record_thread(self, participants):
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
        if not self.thread_filter:
            return True
        if len(participants) != len(self.thread_filter):
            return False
        participants = [[p.lower()] + p.lower().split(" ")
                        for p in participants]
        matches = defaultdict(set)
        for e, p in enumerate(participants):
            for f in self.thread_filter:
                if f in p:
                    matches[f].add(e)
        matched = set()
        for f in matches:
            if len(matches[f]) == 0:
                return False
            matched |= matches[f]
        return len(matched) == len(participants)

    def parse(self):
        self.parse_impl()
        self._clear_output()
        return FacebookChatHistory(self.user, self.chat_threads)

    def parse_impl(self):
        #
        # Implementation details:
        #
        #  1. Load the file/manifest.
        #  2. Parse the user.
        #  3. Facilitate the parsing of a thread by identifying
        #     participants and providing an element iterator.
        #  4. Save the thread.
        #  5. Return the history object.
        #
        raise NotImplementedError

    def parse_thread(self, participants, element_iter, require_flush):
        """
        Parses a thread with appropriate CLI feedback.

        :param participants: The participants in this thread.
        :param element_iter: The XML iterator to parse the data from.
        :param require_flush: Whether the iterator needs to be flushed if it is
                              determined that the thread should be skipped.
        :return: A `ChatThread` object if not skipped, otherwise `None`.
        """

        # Very rarely threads may lack information on who the
        # participants are. We will consider those threads corrupted
        # and skip them.
        participants_text = _truncate(', '.join(participants), 60)
        if participants:
            skip_thread = not self.should_record_thread(participants)
            participants_text = yellow("[%s]" % participants_text)
        else:
            participants_text = "unknown participants"
            skip_thread = True
        if skip_thread:
            line = "\rSkipping chat thread with %s..." % \
                   yellow(participants_text)
        else:
            participants_key = ", ".join(participants)
            if participants_key in self.chat_threads:
                thread_current_len = len(self.chat_threads[participants_key])
                line = "\rContinuing chat thread with %s %s..." \
                       % (yellow(participants_text), magenta("<@%d messages>" % thread_current_len))
            else:
                line = "\rDiscovered chat thread with %s..." \
                       % yellow(participants_text)
        if self.progress_output:
            sys.stderr.write(line.ljust(self.last_line_len))
            sys.stderr.flush()
        self.last_line_len = len(line)

        parser = ChatThreadParser(
            element_iter, self.timezone_hints, self.use_utc, self.name_resolver,
            self.no_sender_warning, self.seq_num)

        if skip_thread:
            if require_flush:
                parser.skip()
        else:
            self.no_sender_warning, thread = parser.parse(participants)
            return thread

    def save_thread(self, thread):

        if thread is None:
            return

        signature = thread.signature

        if signature in self.thread_signatures:
            # FIXME: Suppressed until use of a logging library is
            #        implemented
            # error("Duplicate thread detected: %s\n "
            #        % str(self.current_thread.participants))
            return

        participants = ", ".join(thread.participants)
        self.thread_signatures.add(signature)

        if participants not in self.chat_threads:
            self.chat_threads[participants] = thread
        else:
            existing_thread = self.chat_threads[participants]
            for m in thread.messages:
                existing_thread.add_message(m)

    def parse_participants(self, participants_element):
        if not participants_element.text:
            return ()
        if participants_element.attrib:
            participants_text = participants_element.text.strip()
        else:
            participants_text = participants_element.contents[0].strip()
        participants = [self.name_resolver.resolve(p)
                        for p in participants_text.split(", ")]
        participants.sort()
        if self.user in participants:
            participants.remove(self.user)
        return tuple(participants)

    def _clear_output(self):
        """
        Clears progress output (if any) that was written to the screen.
        """
        # If progress output was being written, clear it from the screen.
        if self.progress_output:
            sys.stderr.write("\r".ljust(self.last_line_len))
            sys.stderr.write("\r")
            sys.stderr.flush()


def using_windows():
    return 'windows' in platform.platform().lower()


class LegacyMessageHtmlParser(MessageHtmlParser):
    """
    A parser for the original archive format Facebook used until October 2017.
    """

    def parse_impl(self):
        """
        Parses the HTML content as a stream. This is far less memory
        intensive than loading the entire HTML file into memory, like
        BeautifulSoup does.
        """

        # Cast to str to ensure not unicode under Python 2, as the parser
        # doesn't like that.
        parser = XMLParser(encoding=str('UTF-8'))
        element_iter = ET.iterparse(self.handle, events=("start", "end"), parser=parser)
        for pos, element in element_iter:
            tag, class_attr = _tag_and_class_attr(element)
            if tag == "h1" and pos == "end":
                if not self.user:
                    self.user = element.text.strip()
            elif tag == "div" and "thread" in class_attr and pos == "start":
                participants = self.parse_participants(element)
                thread = self.parse_thread(participants, element_iter, True)
                self.save_thread(thread)


class SplitMessageHtmlParser(MessageHtmlParser):
    """
    A parser for the archive format Facebook started using around October 2017.
    """

    def __init__(self, handle, *args, **kwargs):
        super(SplitMessageHtmlParser, self).__init__(handle, *args, **kwargs)
        self.root = os.path.realpath(handle.name)
        delimiter = '\\' if using_windows() else '/'
        self.root = delimiter.join(self.root.split(delimiter)[:-2])

    def parse_impl(self):

        ignore_anchors = True
        saw_anchor = False

        # Cast to str to ensure not unicode under Python 2, as the parser
        # doesn't like that.
        parser = XMLParser(encoding=str('UTF-8'))
        element_iter = ET.iterparse(self.handle, events=("start", "end"), parser=parser)
        for pos, element in element_iter:
            tag, class_attr = _tag_and_class_attr(element)
            if tag == "h1" and pos == "end":
                if not self.user:
                    self.user = element.text.strip()
            elif tag == "div" and "content" in class_attr and pos == "start":
                ignore_anchors = False
            elif tag == "a" and pos == "start":
                if ignore_anchors:
                    continue
                saw_anchor = True
                participants = self.parse_participants(element)
                thread_path = re.sub(r'^../', '', element.attrib['href'])
                if using_windows():
                    thread_path = thread_path.replace('/', '\\')
                self.process_thread(participants, thread_path)

        if not saw_anchor:
            # Indicator of a `messages.htm` file that is probably in the legacy format.
            raise UnsuitableParserError

        self._clear_output()
        return FacebookChatHistory(self.user, self.chat_threads)

    def process_thread(self, participants, thread_path):

        file_path = os.path.join(self.root, thread_path)

        try:
            with io.open(file_path, 'rt', encoding='utf8') as thread_file:
                parser = XMLParser(encoding=str('UTF-8'))
                element_iter = ET.iterparse(
                    SafeXMLStream(thread_file), events=("start", "end"), parser=parser)
                thread = self.parse_thread(participants, element_iter, False)
        except FileNotFoundError:
            raise MissingReferenceError(file_path)
        self.save_thread(thread)


def parse(handle, *args, **kwargs):
    for parser in (SplitMessageHtmlParser, LegacyMessageHtmlParser):
        try:
            return parser(handle, *args, **kwargs).parse()
        except UnsuitableParserError:
            # Rewind for the next parser.
            handle.seek(0)
    raise UnsuitableParserError("no suitable parser found")
