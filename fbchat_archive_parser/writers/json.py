import json

class Writer(object):

	def write(self):
		

	def _write_history(self):
        raise NotImplementedError('subclasses of Writer must provide a _write_history() method')

   	def _write_thread(self):
    	raise NotImplementedError('subclasses of Writer must provide a _write_thread() method')

	def _write_message(self):
    	raise NotImplementedError('subclasses of Writer must provide a _write_message() method')