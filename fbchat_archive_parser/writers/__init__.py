from __future__ import unicode_literals

from datetime import datetime
import io
import os
import shutil

import six

from .json import JsonWriter
from .pretty_json import PrettyJsonWriter
from .csv import CsvWriter
from .stats import StatsWriter
from .text import TextWriter
from .yaml import YamlWriter

if six.PY2:
    FileNotFoundError = OSError

_BUILTIN_WRITERS = {
    "json": JsonWriter,
    "pretty-json": PrettyJsonWriter,
    "csv": CsvWriter,
    "text": TextWriter,
    "yaml": YamlWriter,
    "stats": StatsWriter
}

BUILTIN_WRITERS = tuple(sorted(list(_BUILTIN_WRITERS.keys())))


class SerializerDoesNotExist(KeyError):
    """The requested serializer was not found."""
    pass


def write(fmt, data, stream_or_dir):
    if fmt not in _BUILTIN_WRITERS:
        raise SerializerDoesNotExist("No such serializer '%s'" % fmt)
    selected_writer = _BUILTIN_WRITERS[fmt]
    if isinstance(stream_or_dir, six.string_types):
        write_to_dir(selected_writer(), stream_or_dir, data)
    else:
        selected_writer().write(data, stream_or_dir)


def write_to_dir(writer, directory, data):

    output_dir = datetime.now().strftime("fbchat_dump_%Y%m%d%H%M")
    directory = os.path.join(directory, output_dir)

    try:
        shutil.rmtree(directory)
    except FileNotFoundError:
        pass
    os.makedirs(directory)

    ordered_threads = [data.threads[k] for k in sorted(list(data.threads.keys()))]

    # Write the manifest
    with io.open("%s/manifest.txt" % directory, 'w', encoding='utf-8') as manifest:
        manifest.write("Chat history manifest for: %s\n\n" % data.user)
        for i, thread in enumerate(ordered_threads, start=1):
            manifest.write("  %s. %s\n" % (i, ", ".join(thread.participants)))

    # Write each thread.
    for i, thread in enumerate(ordered_threads, start=1):
        thread_file_str = "%s/thread_%s.%s" % (directory, i, writer.extension)
        with io.open(thread_file_str, 'w', encoding='utf-8') as thread_file:
            writer.write_thread(thread, stream=thread_file)

    print("Thread content written to [%s]" % directory)
