from fbchat_archive_parser import ChatThread, ChatMessage, FacebookChatHistory

class SerializerDoesNotExist(KeyError):
    """The requested serializer was not found."""
    pass

class UnserializableObject():
	

class Writer(object):

	def write(self, data):
		if isinstance(data, FacebookChatHistory):
			return self._write_history(data)
		elif isinstance(data, ChatThread):
			return self._write_thread(data)
		elif isinstance(data, ChatMessage):
			return self._write_message(data)
		else:


	def _write_history(self, data):
        raise NotImplementedError('subclasses of Writer must provide a _write_history() method')

   	def _write_thread(self, data):
    	raise NotImplementedError('subclasses of Writer must provide a _write_thread() method')

	def _write_message(self, data):
    	raise NotImplementedError('subclasses of Writer must provide a _write_message() method')