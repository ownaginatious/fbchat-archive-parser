Facebook Chat Archive Parser |Build Status|
===========================================

A small tool and library for parsing chat history from a Facebook data
archive into more usable formats.

What is a "Facebook Chat Archive"?
----------------------------------

Facebook Messenger records all your conversation history since the
beginning of time. If you want it back for some reason, you have two
options:

1. Create a scraper that constantly "scrolls up" in the conversation
   window you're interested in (or simulates that with API calls),
   progressively getting more and more of your chat history.

2. Ask Facebook for an archive of *all* your data
   `here <https://www.facebook.com/dyi>`__ , and wait a couple of days
   for them to give it to you as a zip archive.

Number 2 is the only practical option if you want *everything* in a
timely manner.

What does Facebook give me in this zip archive?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Facebook gives you literally everything you've ever posted to Facebook,
which includes your pictures, videos, posts. etc in addition to your
chat messages.

Your chat history comes in a single HTML page titled ``messages.htm``.
Unfortunately, the data is mostly unordered and impossible to load into
your web browser (it can be several hundred megabytes in size). You're
essentially forced to parse it if you want to analyze the content.

Why would I ever want my Facebook chat history?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are a number of reasons you may want to parse your Facebook chat
history:

1. To make a simulation of your friends using `Markov
   chains <https://en.wikipedia.org/wiki/Markov_chain>`__.
2. You're deleting your Facebook account, but would like a record of
   your conversations.
3. You need to analyze a copy of your conversations for legal reasons.

Here comes the Facebook Chat Archive Parser!
--------------------------------------------

The Facebook Chat Archive Parser is a command line tool (and library for
advanced users) for easily transforming your ``messages.htm`` file into
something actually useful.

How do I get it?
~~~~~~~~~~~~~~~~

Install the Facebook Chat Archive Parser via ``pip`` under at least
Python 2.7:

.. code:: bash

    pip install fbchat-archive-parser

How does it work?
~~~~~~~~~~~~~~~~~

Simply run the command ``fbcap`` in your terminal with your
``messages.htm`` file as the argument.

.. code:: bash

    fbcap ./messages.htm

And watch as the parser sifts through your data!

.. figure:: https://zippy.gfycat.com/SpitefulSnivelingBluebreastedkookaburra.gif
   :alt: Processing gif

When it's done, it will dump all your conversation history is dumped to
``stdout``. Obviously, this can be very long, so here is an example:

.. figure:: http://i.imgur.com/ZgHjUST.png
   :alt: Results

What if I want JSON?
~~~~~~~~~~~~~~~~~~~~

Simply supply the ``-f json`` option to the command line:

.. code:: bash

    fbcap ./messages.htm -f json

The output format is as follows:

    Messages are ordered from oldest to newest.

.. code:: json

    {
        "threads": [
            {
                "participants": ["participant_0", "...", "participant_n"],
                "messages": [
                    {
                        "date": "ISO 8601 formatted date",
                        "sender": "sender name",
                        "message": "message text"
                    },
                    "..."
                ]
            },
            "..."
        ]
    }

How about CSV?
~~~~~~~~~~~~~~

Of course!

.. code:: bash

    fbcap ./messages.htm -f csv

.. code:: text

    thread,sender,date,message
    Third User,Third User,2013-10-04T15:05Z,1
    Third User,Third User,2013-10-04T15:05Z,2
    Third User,Third User,2013-10-04T15:05Z,3
    Third User,First User,2013-10-04T15:05Z,4
    Third User,Third User,2013-10-04T15:06Z,5
    Third User,First User,2013-10-04T15:07Z,6
    Third User,First User,2013-10-04T15:07Z,7
    Second User,Second User,2013-10-04T15:04Z,X Y Z
    Second User,Second User,2013-10-04T15:05Z,X? Y Z!
    Second User,Second User,2013-10-04T15:05Z,This is a test
    Second User,Second User,2013-10-04T15:05Z,"Yes, it is"
    Second User,Second User,2013-10-04T15:05Z,The last message!
    "Second User, Third User",Third User,2013-10-04T15:05Z,1
    "Second User, Third User",Third User,2013-10-04T15:05Z,2
    ...

What about that YAML thing the kids these days are talking about?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For sure!

.. code:: bash

    fbcap ./messages.htm -f yaml

.. code:: text

    user: First User
    threads:
    - participants:
      - Second User
      - Third User
      messages:
      - date: 2013-10-04T22:05-07:00
        message: '1'
        sender: Third User
      - date: 2013-10-04T22:05-07:00
        message: '2'
        sender: Third User
      - date: 2013-10-04T22:05-07:00
        message: '3'
        sender: Third User
    ...

What if I want to see some statistics?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See who you talk to the most among your friends and how much each of you
contribute to the conversation.

.. code:: bash

    fbcap ./messages.htm -f stats

.. figure:: http://i.imgur.com/U2T6KwC.png
   :alt: stats image

How do I get any of the above into a file?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Just use standard file redirects.

.. code:: bash

    fbcap ./messages.html > my_file.txt

What if I only want to parse out a specific conversation?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use the ``-t`` option to specify a particular
conversation/thread you want to output. Just provide a comma-separated
set of names. If you don't remember a last name (or conversely, only
remember the last name), the system will try to compensate.

.. code:: bash

    fbcap ./messages.html -t second

.. figure:: http://i.imgur.com/3FbWIN7.png
   :alt: filter second

.. code:: bash

    fbcap ./messages.html -t second,third

.. figure:: http://i.imgur.com/IJzD1LE.png
   :alt: filter second and third

What else can I do?
===================

Take a look at the help options to find out more!

.. code:: text

    $ fbcap --help
    fbcap: A program for converting Facebook chat history to a number of more usable formats

    Usage: fbcap {{arguments}} {{options}}

    Arguments:
      path [text]  Path of the messages.htm file to parse

    Options:
      -h, --help              Show this help message and exit
      -f, --format [str]      Format to convert to (json, csv, text, yaml, stats) (default: text)
      -t, --thread [text]     Only include threads involving exactly the following comma-separated participants in output (-t 'Billy,Steve Jensson')
      -z, --timezones [text]  Timezone disambiguators (TZ=OFFSET,[TZ=OFFSET[...]])
      -u, --utc               Use UTC timestamps in the output
      -n, --nocolor           Do not colorize output
      -p, --noprogress        Do not show progress output

.. |Build Status| image:: https://travis-ci.org/ownaginatious/fbchat-archive-parser.svg?branch=master
   :target: https://travis-ci.org/ownaginatious/fbchat-archive-parser
