Facebook Chat Archive Parser
============================

|PyPI Version| |Python Versions| |Build Status|

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

**UPDATE:** As of October 2017, ``messages.htm`` just acts as a manifest
for the contents of a directory called ``messages/``. The formatting is
almost identical to before; just with each thread in its own file now.
Both are required to use this tool.

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

If you already have an older version installed, you can upgrade to the latest with the following command:

.. code:: bash

    pip install --upgrade fbchat-archive-parser

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

    fbcap ./messages.htm > my_file.txt

Can I get each conversation into a separate file?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the ``-d`` directive to send the output to a directory instead.

.. code:: bash

    fbcap ./messages.htm -d some/random/directory

This will create a file per conversation titled ``thread_#.ext`` where # is the conversation number and
ext is the extension of the format (e.g. ``json``). A ``manifest.txt`` file is also created, which lists
the participants in each thread number for navigational/search purposes.

What if I only want to parse out a specific conversation?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use the ``-t`` option to specify a particular
conversation/thread you want to output. Just provide a comma-separated
set of names. If you don't remember a last name (or conversely, only
remember the last name), the system will try to compensate.

.. code:: bash

    fbcap ./messages.htm -t second

.. figure:: http://i.imgur.com/3FbWIN7.png
   :alt: filter second

.. code:: bash

    fbcap ./messages.htm -t second,third

.. figure:: http://i.imgur.com/IJzD1LE.png
   :alt: filter second and third

What else can I do?
===================

Take a look at the help options to find out more!

.. code:: text

    $ fbcap --help
    Usage: fbcap [OPTIONS] PATH

      A program for converting Facebook chat history (messages.htm) to a number
      of more usable formats.

    Options:
      -f, --format [csv|json|pretty-json|text|yaml|stats]
                                      Format to convert to.
      -t, --thread TEXT               Only include threads involving exactly the
                                      following comma-separated participants in
                                      output (-t 'Billy,Steve Smith')
      -z, --timezones TEXT            Timezone disambiguators
                                      (TZ=OFFSET,[TZ=OFFSET[...]])
      -d, --directory PATH            Write all output as a file per thread into a
                                      directory (subdirectory will be created)
      -u, --utc                       Use UTC timestamps in the output
      -n, --nocolor                   Do not colorize output
      -p, --noprogress                Do not show progress output
      -r, --resolve                   [BETA] Resolve profile IDs to names by
                                      connecting to Facebook
      --help                          Show this message and exit.

Troubleshooting
===============

Why do some names appear as <some number>@facebook.com?
-------------------------------------------------------

For some reason, Facebook seems to randomly swap names for IDs. In recent times, it has gotten worse. You can
have the parser resolve the names via Facebook itself with the ``--resolve`` flag. Keep in mind, this is a beta
feature and may not work perfectly.

.. code:: text

    $ fbcap ./messages.htm -t second --resolve
    Facebook username/email: facebook_username
    Facebook password:

This requires your Facebook credentials to get accurate results. This does not relay your credentials through
any servers and is a direct connection from your computer to Facebook. Please look at the code if you are
feeling paranoid or skeptical :)

Why are some of my chat threads missing?
----------------------------------------

This is a mysterious issue on Facebook's end. From anecdotal evidence, it seems that what gets returned in your
chat archive is generally conversations with people who you have most recently talked to. Fortunately, it always
seems to be the complete history for each conversation and nothing gets truncated.

Unfortunately, this cannot be remedied unless Facebook fixes the problem on their end.

.. |PyPI Version| image:: https://badge.fury.io/py/fbchat-archive-parser.svg
    :target: https://badge.fury.io/py/fbchat-archive-parser

.. |Python Versions| image:: https://img.shields.io/pypi/pyversions/fbchat-archive-parser.svg
    :target: https://github.com/ownaginatious/fbchat-archive-parser/blob/master/setup.py

.. |Build Status| image:: https://travis-ci.org/ownaginatious/fbchat-archive-parser.svg?branch=master
   :target: https://travis-ci.org/ownaginatious/fbchat-archive-parser
