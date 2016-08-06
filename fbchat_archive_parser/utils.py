import sys
from colorama import Fore, Style, init

def set_color(nocolor):
    init(strip=nocolor or not sys.stdout.isatty())

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
