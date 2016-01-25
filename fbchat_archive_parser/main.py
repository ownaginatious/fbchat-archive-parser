import clip
import sys
from .writers import BUILTIN_WRITERS, write
from .parser import FacebookChatHistory
from colorama import init, Back, Fore, Style
from collections import Counter

app = clip.App()


@app.main(description='A program for converting Facebook chat history to a '
                      'number of more usable formats')
@clip.opt('-f', '--format', default='text',
          help='Format to convert to (%s)' %
               ', '.join(BUILTIN_WRITERS + ('stats',)))
@clip.opt('-t', '--thread', default=None,
          help='Only include threads involving the following '
               'comma-separated people (-t \'Billy,Steve Jensson)')
@clip.flag('-n', '--nocolor', help='Do not colorize output')
@clip.arg('path', required=True, help='Path of the messages.htm file to parse')
def fbcap(path, thread, format, nocolor):
    init(strip=nocolor or not sys.stdout.isatty())
    fbch = FacebookChatHistory(path, progress_output=sys.stdout.isatty())
    if thread:
        include = set(thread.lower().split(','))
        remove = []
        for participants in fbch.chat_threads.keys():
            p_lower = tuple(p.lower() for p in participants)
            if len(include & set(p_lower)) > 0:
                continue
            if len(include & set(" ".join(p_lower).split(" "))) > 0:
                continue
            remove += [participants]
        for p in remove:
            del fbch.chat_threads[p]
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
    top_10 = enumerate(sorted(threads, key=lambda t: len(t))[::-1][0:10], 1)
    for i, t in top_10:
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
                         " [" + str(round((c * 100) / total, 2)) + "]" +
                         Fore.RESET + '\n')
        stream.write('\n')


def main():
    try:
        app.run()
    except clip.ClipExit:
        pass

if __name__ == '__main__':
    main()
