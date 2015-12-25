from parser import ChatThread, ChatMessage, FacebookChatHistory
from writer import JsonWriter

BUILTIN_WRITERS = {
	"json": "writers"
}

def serialize(format, history):
	pass