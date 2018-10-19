# coding=utf-8
import os

import yaml

from .utils import write_data_to_file


def read_yaml_file(fn):
    assert os.path.exists(fn)
    # noinspection PyUnresolvedReferences
    # try:
    #     import ruamel.ordereddict as s
    # except ImportError:
    #     pass
    # from ruamel import yaml
    with open(fn) as f:
        data = f.read()
        return yaml.load(data, Loader=yaml.Loader)


def write_yaml(data, fn):
    # from ruamel import yaml
    y = yaml.dump(data, default_flow_style=False)
    write_data_to_file(y, fn)
