# coding=utf-8
import os

import oyaml as yaml

from .utils import write_data_to_file


def read_yaml_file(fn):
    if not os.path.exists(fn):
        msg = 'File does not exist: %s' % fn
        raise ValueError(msg)
    with open(fn) as f:
        contents = f.read()
    return interpret_yaml_string(contents)


def interpret_yaml_string(s):
    # if s.startswith('!!omap'):
    #     s = s.replace('!!omap', '')
    res = yaml.load(s, Loader=yaml.Loader)
    if s.strip().startswith('!!omap'):
        res = dict(res)
    return res


def write_yaml(data, fn):
    y = yaml.dump(data, default_flow_style=False)
    write_data_to_file(y, fn)
