Facebook Chat Archive Parser
============================

|PyPI Version| |Python Versions| |Build Status|

A small tool and library for parsing chat history from a Facebook data
archive into more usable formats.

What is a "Facebook Chat Archive"?
----------------------------------

Facebook Messenger records all your conversation history since your account's creation.
There are two options for history retrieval:

1. Create a scraper that constantly "scrolls up" in the conversation
   window you're interested in (or simulates that with API calls),
   progressively getting more of your chat history.

2. Ask Facebook for a zip archive of *all* your data
   `here <https://www.facebook.com/dyi>`__ .

The second option is the only practical way to obtain *everything* in a
timely manner.

What does Facebook give me in this zip archive?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The zip archive contains everything you've ever posted to Facebook,
including: pictures, videos, posts. etc along with chat messages.

Your chat history comes in a single HTML page titled ``messages.htm``.
Unfortunately, the data is unordered and impossible to load into
a web browser since it can be hundreds of megabytes. The only way to analyze
the content is through parsing the file.

**UPDATE:** As of October 2017, ``messages.htm`` just acts as a manifest
for the contents of a directory called ``messages/``. The formatting is
almost identical to before but with each thread in its own file now.
All files are required to use this tool.

Why would I ever want my Facebook chat history?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here are some reasons you may want to parse your Facebook chat
history:

1. To make a simulation of your friends using `Markov
   chains <https://en.wikipedia.org/wiki/Markov_chain>`__.
2. To keep a record of your conversations when deleting your Facebook account.
3. To analyze a copy of your conversations for legal reasons.

Here comes the Facebook Chat Archive Parser!
--------------------------------------------

The Facebook Chat Archive Parser is a command line tool (and library for
advanced users) used to easily transform your ``messages.htm`` file into
a useful format.

How do I get it?
~~~~~~~~~~~~~~~~

Install the Facebook Chat Archive Parser via ``pip`` under
Python 2.7 or newer:

.. code:: bash

    pip install fbchat-archive-parser

If you already have an older version installed, you can upgrade to the latest with the following command:

.. code:: bash

    pip install --upgrade fbchat-archive-parser

How does it work?
~~~~~~~~~~~~~~~~~

Under the ``html/`` folder simply run the command ``fbcap`` in your terminal with your
``messages.htm`` file as the argument.

.. code:: bash

    fbcap messages ./messages.htm

And watch as the parser sifts through your data!

.. figure:: https://i.imgur.com/HTChSxj.png
   :alt: Processing png

When it's done, your conversation history is dumped to
``stdout``. This can be very long. Here is an example:

.. figure:: http://i.imgur.com/ZgHjUST.png
   :alt: Results

What if I want JSON?
~~~~~~~~~~~~~~~~~~~~

Simply supply the ``-f json`` option to the command line:

.. code:: bash

    fbcap messages ./messages.htm -f json

Or if you want pretty formatted JSON:

.. code:: bash

    fbcap messages ./messages.htm -f pretty-json

The output format is as follows (messages are ordered from oldest to newest).

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

    fbcap messages ./messages.htm -f csv

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

What about YAML?
~~~~~~~~~~~~~~~~

For sure!

.. code:: bash

    fbcap messages ./messages.htm -f yaml

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

You can see many statistics regarding your Facebook chat history via the ``stats`` subcommand in many different formats.

.. code:: bash

    fbcap stats ./messages.htm -f text

.. figure:: http://i.imgur.com/Dwzevxu.png
   :alt: stats image

See the ``--help`` menu for instructions on how to control what appears in the stats.

.. code:: text

    $ fbcap stats --help
    Usage: fbcap stats [OPTIONS] PATH

      Analysis of Facebook chat history.

    Options:
      -f, --format [json|pretty-json|text|yaml]
                                      Format to output stats as (default: text).
      -c, --count-size INTEGER        Number of most frequent words to include in
                                      output (-1 for no limit / default 10)
      -l, --length INTEGER            Number threads to include in the output
                                      [--fmt text only] (-1 for no limit / default
                                      10)
      -r, --resolve                   [BETA] Resolve profile IDs to names by
                                      connecting to Facebook
      -p, --noprogress                Do not show progress output
      -n, --nocolor                   Do not colorize output
      -u, --utc                       Use UTC timestamps in the output
      -z, --timezones TEXT            Timezone disambiguators
                                      (TZ=OFFSET,[TZ=OFFSET[...]])
      --help                          Show this message and exit.

How do I get any of the above into a file?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use standard file redirects.

.. code:: bash

    fbcap messages ./messages.htm > my_file.txt

Can I get each conversation into a separate file?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the ``-d`` directive to send the output to a directory instead.

.. code:: bash

    fbcap messages ./messages.htm -d some/random/directory

This will create a file per conversation titled ``thread_#.ext`` where # is the conversation number and ext is the extension of the format (e.g. ``json``). A ``manifest.txt`` file is also created, which lists the participants in each thread number for navigational/search purposes.

What if I only want to parse out a specific conversation?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use the ``-t`` option to specify a particular conversation/thread you want to output. Just provide a comma-separated set of names. If you don't remember a last name (or the first name), the system will try to compensate.

.. code:: bash

    fbcap messages ./messages.htm -t second

.. figure:: http://i.imgur.com/3FbWIN7.png
   :alt: filter second

.. code:: bash

    fbcap messages ./messages.htm -t second,third

.. figure:: http://i.imgur.com/IJzD1LE.png
   :alt: filter second and third

What happens to my messages that are pictures?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As of January 2018, Facebook seems to be including referenced images in download archives. Image
messages will be converted to text references in the following format:
``(image reference: messages/photos/<picture id>.jpg)``

What else can I do?
===================

Take a look at the help options to find out more!

.. code:: text

    $ fbcap messages --help
    Usage: fbcap messages [OPTIONS] PATH

      Conversion of Facebook chat history.

    Options:
      -f, --format [csv|json|pretty-json|text|yaml]
                                      Format to convert to.
      -t, --thread TEXT               Only include threads involving exactly the
                                      following comma-separated participants in
                                      output (-t 'Billy,Steve Smith')
      -d, --directory PATH            Write all output as a file per thread into a
                                      directory (subdirectory will be created)
      -r, --resolve                   [BETA] Resolve profile IDs to names by
                                      connecting to Facebook
      -p, --noprogress                Do not show progress output
      -n, --nocolor                   Do not colorize output
      -u, --utc                       Use UTC timestamps in the output
      -z, --timezones TEXT            Timezone disambiguators
                                      (TZ=OFFSET,[TZ=OFFSET[...]])
      --help                          Show this message and exit.

Troubleshooting
===============

Why do some names appear as <some number>@facebook.com?
-------------------------------------------------------

Facebook seems to randomly swap names for IDs. As of late, this seems to be much less of an issue. Nevertheless, if you are experiencing this issue, the parser can resolve the names via Facebook with the ``--resolve`` flag. Keep in mind, this is a beta feature and may not work perfectly.

.. code:: text

    $ fbcap messages ./messages.htm -t second --resolve
    Facebook username/email: facebook_username
    Facebook password:

This requires your Facebook credentials to get accurate results. This is a direct connection between your computer and Facebook.
Your credentials are not relayed through any servers. Please look at the code if you are feeling paranoid or skeptical :)

Why are some of my chat threads missing?
----------------------------------------

This is a mysterious issue on Facebook's end. From anecdotal evidence, it seems that what gets returned in your chat archive is generally conversations with people who you have most recently talked to. Fortunately, it always seems to be the complete history for each conversation and nothing gets truncated.

As of late, it seems like Facebook has fixed this issue on their end and it is now far less of an issue.

Why are repeated names not showing?
-----------------------------------

Multiple users with equal names in group chats are shown as a single user. This has to do with Facebook's presentation of names in the message files, which doesn't make this distinction.

This cannot be remedied unless Facebook fixes the problem.

.. |PyPI Version| image:: https://badge.fury.io/py/fbchat_archive_parser.svg
    :target: https://pypi.org/project/fbchat_archive_parser/

.. |Python Versions| image:: https://img.shields.io/pypi/pyversions/fbchat-archive-parser.svg
    :target: https://github.com/ownaginatious/fbchat-archive-parser/blob/master/setup.py

.. |Build Status| image:: https://travis-ci.org/ownaginatious/fbchat-archive-parser.svg?branch=master
   :target: https://travis-ci.org/ownaginatious/fbchat-archive-parser
