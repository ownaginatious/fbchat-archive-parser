from __future__ import unicode_literals

from collections import Counter
import re
import sys

import clip

from .writers import BUILTIN_WRITERS, write
from .parser import MessageHtmlParser
from .time import AmbiguousTimeZoneError, UnexpectedTimeFormatError
from .utils import set_color, green, bright, cyan, error, \
                   reset_terminal_styling

# Python 3 is supposed to be smart enough to not ever default to the 'ascii'
# encoder, but apparently on Windows that may not be the case.
if sys.version_info >= (3, 0):

    import io
    # Change the output streams to binary.
    sys.stderr = sys.stderr.detach()
    sys.stdout = sys.stdout.detach()

    # Wrap them in a safe UTF-8 encoders. PDB doesn't like it when
    # the streams are wrapped in StreamWriter.
    sys.stdout = io.TextIOWrapper(sys.stdout, encoding='UTF-8',
                                  errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr, encoding='UTF-8',
                                  errors='replace')

else:

    from encodings.utf_8 import StreamWriter
    # Wrap the raw Python 2 output streams in smart UTF-8 encoders.
    # Python 2 doesn't like it when the raw file handles are wrapped in
    # TextIOWrapper.
    sys.stderr = StreamWriter(sys.stderr)
    sys.stdout = StreamWriter(sys.stdout)

app = clip.App()


@app.main(description='A program for converting Facebook chat history to a '
                      'number of more usable formats')
@clip.opt('-f', '--format', default='text',
          help='Format to convert to (%s)' %
               ', '.join(BUILTIN_WRITERS + ('stats',)))
@clip.opt('-t', '--thread', default=None,
          help='Only include threads involving exactly the following '
               'comma-separated participants in output '
               '(-t \'Billy,Steve Jensson\')')
@clip.opt('-z', '--timezones',
          help='Timezone disambiguators (TZ=OFFSET,[TZ=OFFSET[...]])')
@clip.flag('-u', '--utc', help='Use UTC timestamps in the output')
@clip.flag('-n', '--nocolor', help='Do not colorize output')
@clip.flag('-p', '--noprogress', help='Do not show progress output')
@clip.arg('path', required=True, help='Path of the messages.htm file to parse')
def fbcap(path, thread, format, nocolor, timezones, utc, noprogress):

    # Make stderr colorized unless explicitly disabled.
    set_color(sys.stderr, disabled=nocolor or not sys.stderr.isatty())
    set_color(sys.stdout, disabled=nocolor or not sys.stdout.isatty())

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
                offset = (neg * int(offset_raw[1:3]),
                          neg * int(offset_raw[3:]))
                timezone_hints[name] = offset
        except Exception:
            error("Invalid timezone string: %s\n" % timezones)
            sys.exit(1)

    # Filter duplicate spaces in thread filters.
    if thread:
        thread = re.sub("\s+", " ", thread)
        thread = tuple(friend.strip() for friend in thread.split(","))

    exit_code = 0
    try:

        parser = MessageHtmlParser(path=path, filter=thread,
                                   timezone_hints=timezone_hints,
                                   progress_output=not noprogress,
                                   use_utc=utc)
        fbch = parser.parse()
        if format == 'stats':
            generate_stats(fbch, sys.stdout)
        else:
            write(format, fbch, sys.stdout)

    except AmbiguousTimeZoneError as atze:
        error("\nAmbiguous timezone offset found [%s]. Please re-run the "
              "parser with the -z TZ=OFFSET[,TZ=OFFSET2[,...]] flag."
              "(e.g. -z PST=-0800,PDT=-0700). Your options are as "
              "follows:\n" % atze.tz_name)
        for k, v in atze.tz_options.items():
            regions = ', '.join(list(v)[:3])
            error(" -> [%s] for regions like %s\n" % (k[-1], regions))
        exit_code = 1
    except UnexpectedTimeFormatError as utfe:
        error("\nUnexpected time format in \"%s\". If you downloaded your "
              "Facebook data in a language other than English, then it's "
              "possible support may need to be added to this tool.\n\n"
              "Please report this as a bug on the associated GitHub page "
              "and it will be fixed promptly.\n"
              % utfe.time_string)
        exit_code = 1
    except KeyboardInterrupt:
        error("\nInterrupted prematurely by keyboard\n")
        exit_code = 1
    finally:
        reset_terminal_styling()
    sys.exit(exit_code)


def generate_stats(fbch, stream):

    text_string = '---------------' + \
                  ('-' * len(fbch.user)) + '--' + '\n'
    stream.write(bright(text_string))
    stream.write(bright(' Statistics for %s\n' % fbch.user))
    stream.write(bright(text_string))
    stream.write('\n')

    threads = tuple(fbch.threads[k] for k in fbch.threads.keys())
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
