# coding=utf-8

import re

import oyaml as yaml
import yaml.parser
import yaml.reader

from .utils import write_data_to_file


def read_yaml_file(fn):
    """ Reads YAML file using also !include directives. """
    if not os.path.exists(fn):
        msg = 'File does not exist: %s' % fn
        raise ValueError(msg)
    yaml.reader.Reader.NON_PRINTABLE = re.compile(
            u'[^\x09\x0A\x0D\x20-\x7E\x85\xA0-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]')

    try:
        with open(fn) as f:
            res = yaml.load(f, Loader=IncludeLoader)
    except yaml.parser.ParserError as e:
        msg = f'Cannot read file {fn}'
        raise ValueError(msg) from e


    return res


def write_yaml(data, fn):
    y = yaml.dump(data, default_flow_style=False)
    write_data_to_file(y, fn)


import yaml
import os


class IncludeLoader(yaml.SafeLoader):

    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]

        super(IncludeLoader, self).__init__(stream)

    def include(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))

        with open(filename, 'r') as f:
            return yaml.load(f, IncludeLoader)


IncludeLoader.add_constructor('!include', IncludeLoader.include)
