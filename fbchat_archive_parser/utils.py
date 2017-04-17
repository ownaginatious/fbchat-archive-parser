import sys
from colorama import Fore, Style, init


class BinaryStreamWrapper(object):
    """
    Some of the writers do not support colorizing and
    also do not play nicely with the decolorizing wrapper.
    This provides us a shortcut to the original stream
    to avoid issues.
    """

    def __init__(self, binary_stream, new_stream):
        self.__binary_stream = binary_stream
        self.__new_stream = new_stream

    @property
    def binary_stream(self):
        return self.__binary_stream

    def __getattr__(self, name):
        return getattr(self.__new_stream, name)

    def fileno(self):
        raise OSError()


_COLOR_ENABLED = True


def set_stream_color(stream, disabled):
    """
    Remember what our original streams were so that we
    can colorize them separately, which colorama doesn't
    seem to natively support.
    """
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    init(strip=disabled)

    if stream != original_stdout:
        sys.stdout = original_stdout
        sys.stderr = BinaryStreamWrapper(stream, sys.stderr)
    if stream != original_stderr:
        sys.stderr = original_stderr
        sys.stdout = BinaryStreamWrapper(stream, sys.stdout)


def set_all_color(enabled):
    global _COLOR_ENABLED
    _COLOR_ENABLED = enabled


def error(text):
    sys.stderr.write(text)
    sys.stderr.flush()


def colorize(color, text):
    if not _COLOR_ENABLED:
        return text
    return "%s%s%s" % (color, text, Fore.RESET)


def yellow(text):
    return colorize(Fore.YELLOW, text)


def magenta(text):
    return colorize(Fore.MAGENTA, text)


def red(text):
    return colorize(Fore.RED, text)


def cyan(text):
    return colorize(Fore.CYAN, text)


def green(text):
    return colorize(Fore.GREEN, text)


def bright(text):
    return "%s%s%s" % (Style.BRIGHT, text, Style.RESET_ALL)


def reset_terminal_styling():
    sys.stderr.write(Fore.RESET + Style.RESET_ALL)
    sys.stdout.flush()
