import clip
import sys
from .writers import BUILTIN_WRITERS, write
from .parser import FacebookChatHistory

app = clip.App()


@app.main(description='A program for converting Facebook chat history to a '
                      'number of more usable formats')
@clip.opt('-f', '--format', default='text',
          help='Format to convert to (%s)' % ", ".join(BUILTIN_WRITERS))
@clip.flag('-s', '--stats',
           help='Print statistics rather than message content.')
@clip.arg('path', required=True, help='Path of the messages.htm file to parse')
def fbcap(path, format, stats):
    fbc = FacebookChatHistory(path, progress_output=sys.stdout.isatty())
    write(format, fbc)

if __name__ == '__main__':
    try:
        app.run()
    except clip.ClipExit:
        pass
