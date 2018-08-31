import os
import yaml

from .utils import write_data_to_file


def read_yaml_file(fn):
    assert os.path.exists(fn)

    with open(fn) as f:
        data = f.read()
        return yaml.load(data)


def write_yaml(data, fn):
    y = yaml.dump(data)
    write_data_to_file(y, fn)
