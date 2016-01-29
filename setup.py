#! /usr/bin/env python
from setuptools import setup, find_packages
from io import open

setup(
    name='fbchat_archive_parser',
    packages = find_packages (exclude = ["tests",]),
    version='0.3',
    description='A library/command line utility for parsing Facebook chat history',
    author='Dillon Dixon',
    author_email='dillondixon@gmail.com',
    url='https://github.com/ownaginatious/fbchat-archive-parser',
    download_url='https://github.com/ownaginatious/fbchat-archive-parser/tarball/0.3',
    license='MIT',
    keywords=['facebook', 'chat', 'messenger', 'history'],
    classifiers=['Environment :: Console'],
    install_requires = [line.strip ()
                        for line in open ("requirements.txt", "r",
                                    encoding="utf-8").readlines ()],
    entry_points = {
        "console_scripts": [
            "fbcap = fbchat_archive_parser.main:main",
        ],
    },
)
