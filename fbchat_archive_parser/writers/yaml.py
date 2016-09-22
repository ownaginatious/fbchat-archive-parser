from __future__ import unicode_literals, absolute_import
from .dict import DictWriter

import yaml


class YamlWriter(DictWriter):

    def serialize_content(self, data):
        return yaml.safe_dump(data, default_flow_style=False)
