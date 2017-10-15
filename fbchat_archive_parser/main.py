# -*- coding: utf-8 -*-

import re
import sys

import click
import six

from .writers import BUILTIN_WRITERS, write
from .parser import parse, MissingReferenceError
from .time import AmbiguousTimeZoneError, UnexpectedTimeFormatError
from .utils import (set_stream_color, set_all_color, error,
                    reset_terminal_styling)
from .name_resolver import FacebookNameResolver

# Python 3 is supposed to be smart enough to not ever default to the 'ascii'
# encoder, but apparently on Windows that may not be the case.
if six.PY3:

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


def validate_timezones(ctx, param, value):
    timezone_hints = {}
    if value is None:
        return None
    try:
        for tz in value.split(','):
            name, offset_raw = tz.split('=')
            # Solely for validating the timezone early on.
            neg = -1 if offset_raw[0] == '-' else 1
            offset = (neg * int(offset_raw[1:3]),
                      neg * int(offset_raw[3:]))
            timezone_hints[name] = offset
        return timezone_hints
    except Exception:
        raise click.BadParameter(value)


def collect_facebook_credentials(ctx, param, value):

    if not value:
        return
    email = click.prompt(u"Facebook username/email", type=click.STRING)
    password = click.prompt(
        u"Facebook password", type=click.STRING,
        hide_input=True, confirmation_prompt=True)

    return FacebookNameResolver(email, password)


def parse_thread_filters(ctx, param, value):
    if not value:
        return
    thread = re.sub("\s+", " ", value)  # remove extraneous spaces
    return tuple(friend.strip() for friend in thread.split(","))


@click.command()
@click.option('-f', '--format', 'fmt', default='text',
              type=click.Choice(BUILTIN_WRITERS + ('stats',)),
              help='Format to convert to.')
@click.option('-t', '--thread', callback=parse_thread_filters,
              default=None, type=click.STRING,
              help='Only include threads involving exactly the following '
                   'comma-separated participants in output '
                   '(-t \'Billy,Steve Smith\')')
@click.option('-z', '--timezones', callback=validate_timezones, type=click.STRING,
              help='Timezone disambiguators (TZ=OFFSET,[TZ=OFFSET[...]])')
@click.option('-d', '--directory', default=None, type=click.Path(),
              help='Write all output as a file per thread into a directory '
                   '(subdirectory will be created)')
@click.option('-u', '--utc', is_flag=True,
              help='Use UTC timestamps in the output')
@click.option('-n', '--nocolor', is_flag=True,
              help='Do not colorize output')
@click.option('-p', '--noprogress', is_flag=True,
              help='Do not show progress output')
@click.option('-r', '--resolve', callback=collect_facebook_credentials, is_flag=True,
              help='[BETA] Resolve profile IDs to names by connecting to Facebook')
@click.argument('path', type=click.File('rt', encoding='utf8'))
def fbcap(path, thread, fmt, nocolor, timezones, utc, noprogress, resolve, directory):
    """
    A program for converting Facebook chat history (messages.htm) to a number of more
    usable formats.
    """
    if fmt == 'stats' and directory:
        error('Unsupported operation error: Statistics cannot be written to a directory.\n')
        sys.exit(1)

    # Make stderr colorized unless explicitly disabled.
    set_stream_color(sys.stderr, disabled=nocolor or not sys.stderr.isatty())
    set_stream_color(sys.stdout, disabled=nocolor or not sys.stdout.isatty())

    exit_code = 0
    try:
        with path as f:
            fbch = parse(
                handle=f, thread_filter=thread, timezone_hints=timezones,
                progress_output=not noprogress, use_utc=utc, name_resolver=resolve)
        sort_message = u'Sorting messages...'
        sys.stderr.write(sort_message)
        fbch.sort()
        sys.stderr.write('\r%s\r' % (" " * len(sort_message)))

        if directory:
            set_all_color(enabled=False)
        write(fmt, fbch, directory or sys.stdout)

    except AmbiguousTimeZoneError as atze:
        error(u"\nAmbiguous timezone offset found [%s]. Please re-run the "
              u"parser with the -z TZ=OFFSET[,TZ=OFFSET2[,...]] flag."
              u"(e.g. -z PST=-0800,PDT=-0700). Your options are as "
              u"follows:\n" % atze.tz_name)
        for k, v in atze.tz_options.items():
            regions = ', '.join(list(v)[:3])
            error(u" -> [%s] for regions like %s\n" % (k[-1], regions))
        exit_code = 1
    except UnexpectedTimeFormatError as utfe:
        error(u"\nUnexpected time format in \"%s\". If you downloaded your "
              u"Facebook data in a language other than English, then it's "
              u"possible support may need to be added to this tool.\n\n"
              u"Please report this as a bug on the associated GitHub page "
              u"and it will be fixed promptly.\n"
              % utfe.time_string)
        exit_code = 1
    except MissingReferenceError as upe:
        error(u"\nUnable to locate the referenced chat file \"%s\". Please "
              u"ensure that your \"messages.htm\" file is relative to your "
              u"\"messages/\" directory in the following way while parsing:\n\n"
              u"    ├── html/\n"
              u"    │   ├── ...\n"
              u"    │   ├── messages.htm\n"
              u"    ├── messages/\n\n" % upe)
        exit_code = 1

    except KeyboardInterrupt:
        error(u"\nInterrupted prematurely by keyboard\n")
        exit_code = 1
    finally:
        reset_terminal_styling()
    sys.exit(exit_code)


if __name__ == '__main__':
    fbcap()
