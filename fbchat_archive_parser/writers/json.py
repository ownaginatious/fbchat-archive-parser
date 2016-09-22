from __future__ import unicode_literals, absolute_import
from .dict import DictWriter

import json


class JsonWriter(DictWriter):

    def serialize_content(self, data):
        return json.dumps(data)
