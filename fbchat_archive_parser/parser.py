from bs4 import BeautifulSoup
import bs4
from io import open
from datetime import datetime
import pdb
import arrow
from blist import sortedlist

class ChatMessage(object):

    def __init__(self, timestamp, sender, content):
        self.sender = sender
        self.timestamp = timestamp
        self.content = content

    def __lt__(self, other):
        return self.timestamp < other.timestamp


class ChatThread(object):

    def __init__(self, participants):
        self.participants = list(participants)
        self.participants.sort()
        self.messages = sortedlist()

    def add_message(self, message):
        self.messages.add(message)

DATE_FORMAT = "MMMM D, YYYY h:mma Z"

chat_threads = dict()
file_content = open('./messages.htm', 'r', encoding='utf-8')

temp_files = dict()

# Break out the data on disk to reduce RAM overhead.
for line in file_content:
    if 

print("Stand by while the HTML is being loaded...")
doc = BeautifulSoup(file_content, 'html.parser')
raw_chat_threads = doc.find_all("div", {"class": "thread"})
print("Found %s chat threads!" % len(raw_chat_threads))

for rct in raw_chat_threads:
    #pdb.set_trace()
    participants = rct.find(text=True).split(", ")
    participants.sort()
    participants = tuple(participants)
    print("Reading chat thread between [%s]..." % ", ".join(participants))
    ct = chat_threads.get(participants, ChatThread(participants))
    chat_threads[participants] = ct
    raw_messages = rct.find_all("div", {"class": "message"})
    print("-> Found %s chat messages!" % len(raw_messages))
    last_sender = None
    last_timestamp = None
    for rcm in rct:
        if type(rcm) is not bs4.element.Tag:
            continue
        if rcm.name == "div" and "message" in rcm["class"]:
            last_sender = rcm.find("", {"class": "user"}).find(text=True)
            # Stupid Facebook only uses the ambiguous timezone format. Let's hope the time
            # is always in their server's locale and not the user's locale.
            last_timestamp = rcm.find("", {"class": "meta"}).find(text=True).replace("at ", "")
            if "PDT" in last_timestamp:
                last_timestamp = arrow.get(last_timestamp.replace("PDT", "-0700"), DATE_FORMAT)
            elif "PST" in last_timestamp:
                last_timestamp = arrow.get(last_timestamp.replace("PST", "-0800"), DATE_FORMAT)
            else:
                raise Exception("Expected only PST/PDT timezones (found %s). This is a bug." 
                    % last_timestamp)
        elif rcm.name == "p":
            if last_sender is None or last_timestamp is None:
                continue
            ct.add_message(ChatMessage(last_timestamp, last_sender, rcm.text))
            last_sender, last_timestamp = None, None
        else:
            raise Exception("Unexpected content: " + str(rcm))