from collections import Counter
from encodings.utf_8 import StreamWriter
from functools import partial
import sys
import xml.etree.ElementTree as ET

import clip

from .writers import BUILTIN_WRITERS, write
from .parser import FacebookChatHistory, AmbiguousTimeZoneError, \
                    UnexpectedTimeZoneError
from .utils import set_color, green, bright, cyan, error, reset_terminal_styling

# Let's force the output to be UTF-8 to both console and file for Python 2.
# Python 3 is smart enough to not default to the 'ascii' encoder.
if sys.version_info < (3, 0):
    sys.stdout = StreamWriter(sys.stdout)
    sys.stderr = StreamWriter(sys.stderr)

app = clip.App()


@app.main(description='A program for converting Facebook chat history to a '
                      'number of more usable formats')
@clip.opt('-f', '--format', default='text',
          help='Format to convert to (%s)' %
               ', '.join(BUILTIN_WRITERS + ('stats',)))
@clip.opt('-t', '--thread',
          help='Only include threads involving exactly the following '
               'comma-separated participants in output '
               '(-t \'Billy,Steve Jensson\')')
@clip.opt('-z', '--timezones',
          help='Timezone disambiguators (TZ=OFFSET,[TZ=OFFSET[...]])')
@clip.flag('-n', '--nocolor', help='Do not colorize output')
@clip.flag('-p', '--noprogress', help='Do not show progress output')
@clip.arg('path', required=True, help='Path of the messages.htm file to parse')
def fbcap(path, thread, format, nocolor, timezones, noprogress):
    set_color(nocolor)

    if format not in BUILTIN_WRITERS + ('stats',):
        error("\"%s\" is not a valid output format.\n" % format)
        sys.exit(1)

    timezone_hints = {}
    if timezones:
        try:
            for tz in timezones.split(','):
                name, offset_raw = tz.split('=')
                # Solely for validating the timezone early on.
                neg = -1 if offset_raw[0] == '-' else 1
                offset = (neg * int(offset_raw[1:3]), neg * int(offset_raw[3:]))
                timezone_hints[name] = offset
        except Exception:
            error("Invalid timezone string: %s\n" % timezones)
            sys.exit(1)

    parser_call = partial(FacebookChatHistory, stream=path,
                          filter=tuple(thread.split(",")) if thread else None,
                          timezone_hints=timezone_hints,
                          progress_output=sys.stdout.isatty() and not noprogress)
    try:
        try:
            fbch = parse_data(parser_call)
        except ET.ParseError:
            error('The streaming parser crashed due to malformed XML. Falling '
                  'back to the less strict/efficient python html.parser. It '
                  'may take a while before you see output... \n')
            fbch = parse_data(parser_call(bs4=True))

        if format == 'stats':
            generate_stats(fbch, sys.stdout)
        else:
            write(format, fbch)
    except KeyboardInterrupt:
        error("Interupted prematurely by keyboard")
        reset_terminal_styling()
        sys.exit(1)
    except Exception as e:
        reset_terminal_styling()
        raise e


def parse_data(parser_call):
    try:
        return parser_call()
    except AmbiguousTimeZoneError as atze:
        error(
            "\nAmbiguous timezone offset found [%s]. Please re-run the "
            "parser with the -z TZ=OFFSET[,TZ=OFFSET2[,...]] flag."
            "(e.g. -t PST=-0800,PDT=-0700). Your options are as "
            "follows:\n"  % atze.tz_name)
        for k, v in atze.tz_options.items():
            regions = ', '.join(list(v)[:3])
            error(" -> [%s] for regions like %s\n" % (k[-1], regions))
        sys.exit(1)
    except UnexpectedTimeZoneError as uetze:
        error("\nUnexpected timezone format in \"%s\". Please "
              "report this bug.\n" % str(uetze))
        sys.exit(1)


def generate_stats(fbch, stream):

    text_string = '---------------' + \
                  ('-' * len(fbch.user)) + '--' + '\n'
    stream.write(bright(text_string))
    stream.write(bright(' Statistics for %s\n' % fbch.user))
    stream.write(bright(text_string))
    stream.write('\n')

    threads = tuple(fbch.chat_threads[k] for k in fbch.chat_threads.keys())
    stream.write('Top 10 longest threads:\n\n')
    ordered_threads = sorted(threads, key=lambda t: len(t))
    ordered_threads.reverse()
    for i, t in enumerate(ordered_threads[0:10], 1):
        stream.write("  " + cyan('[' + str(i) + '] ') +
                     bright(", ".join(t.participants) +
                     cyan(" (" + str(len(t.messages)) + ")" + "\n")))
        p_count = Counter()
        for m in t.messages:
            p_count[m.sender] += 1
        total = sum(p_count.values())
        for s, c in p_count.most_common():
            stream.write("      - " + s +
                         green(" [%d|%.2f%%]\n" % (c, (c * 100) / total)))
        stream.write('\n')


def main():
    try:
        app.run()
    except clip.ClipExit:
        pass

if __name__ == '__main__':
    main()
