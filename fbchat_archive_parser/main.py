import clip
from encodings.utf_8 import StreamWriter
import sys
from .writers import BUILTIN_WRITERS, write
from .parser import FacebookChatHistory
from colorama import init, Back, Fore, Style
from collections import Counter

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
@clip.flag('-n', '--nocolor', help='Do not colorize output')
@clip.arg('path', required=True, help='Path of the messages.htm file to parse')
def fbcap(path, thread, format, nocolor):
    init(strip=nocolor or not sys.stdout.isatty())
    fbch = FacebookChatHistory(path,
                               filter=tuple(thread.split(","))
                               if thread else None,
                               progress_output=sys.stdout.isatty())
    if format == 'stats':
        generate_stats(fbch, sys.stdout)
    else:
        write(format, fbch)


def generate_stats(fbch, stream):

    text_string = '---------------' + \
                  ('-' * len(fbch.user)) + '--' + '\n'
    stream.write(Style.BRIGHT + text_string)
    stream.write(' Statistics for %s\n' % fbch.user)
    stream.write(text_string)
    stream.write(Style.RESET_ALL + '\n')

    threads = tuple(fbch.chat_threads[k] for k in fbch.chat_threads.keys())
    stream.write('Top 10 longest threads:\n\n')
    ordered_threads = sorted(threads, key=lambda t: len(t))
    ordered_threads.reverse()
    for i, t in enumerate(ordered_threads[0:10], 1):
        stream.write("  " + Fore.CYAN + '[' + str(i) + '] ' + Fore.RESET +
                     Style.BRIGHT + ", ".join(t.participants) +
                     Fore.CYAN + " (" + str(len(t.messages)) + ")" + "\n")
        stream.write(Fore.RESET + Style.RESET_ALL)
        p_count = Counter()
        for m in t.messages:
            p_count[m.sender] += 1
        total = sum(p_count.values())
        for s, c in p_count.most_common():
            stream.write("      - " + s + Fore.GREEN +
                         " [" + str(c) + "|" +
                         str(round((c * 100) / total, 2)) + "%]" +
                         Fore.RESET + '\n')
        stream.write('\n')


def main():
    try:
        app.run()
    except clip.ClipExit:
        pass

if __name__ == '__main__':
    main()
