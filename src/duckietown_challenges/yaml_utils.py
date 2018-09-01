import os

# noinspection PyUnresolvedReferences
import ruamel.ordereddict as s
from ruamel import yaml

from .utils import write_data_to_file


def read_yaml_file(fn):
    assert os.path.exists(fn)

    with open(fn) as f:
        data = f.read()
        return yaml.load(data, Loader=yaml.Loader)


def write_yaml(data, fn):
    y = yaml.dump(data, default_flow_style=False)
    write_data_to_file(y, fn)
