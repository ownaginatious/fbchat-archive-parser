from __future__ import unicode_literals, absolute_import
from .dict import DictWriter

import json


class PrettyJsonWriter(DictWriter):

    def serialize_content(self, data):
        return json.dumps(data, sort_keys=True, indent=4, ensure_ascii=False)

    @property
    def extension(self):
        return 'json'
