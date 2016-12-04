import sys
from colorama import Fore, Style, init


def set_color(stream, disabled):
    """
    Remember what our original streams were so that we
    can colorize them separately, which colorama doesn't
    seem to natively support.
    """
    original_stderr = sys.stderr
    original_stdout = sys.stdout

    init(strip=disabled)

    if stream != original_stdout:
        sys.stdout = original_stdout
    if stream != original_stderr:
        sys.stderr = original_stderr


def error(text):
    sys.stderr.write(text)
    sys.stderr.flush()


def colorize(color, text):
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
