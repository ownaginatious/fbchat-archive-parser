from __future__ import unicode_literals, absolute_import

import six
import yaml

from .dict import DictWriter


class YamlWriter(DictWriter):

    def serialize_content(self, data):
        data = yaml.safe_dump(data, default_flow_style=False, allow_unicode=True)

        if six.PY2:
            return data.decode('utf8')
        return data
