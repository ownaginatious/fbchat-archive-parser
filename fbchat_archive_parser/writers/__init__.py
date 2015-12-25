from parser import ChatThread, ChatMessage, FacebookChatHistory
from writer import JsonWriter

BUILTIN_WRITERS = {
	"json": "writers.json",
	"csv": "writers.csv"
}

def write(format, history):
	pass