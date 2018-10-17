import os
import subprocess
import traceback
from collections import namedtuple

import yaml

from duckietown_challenges.challenge import SubmissionDescription

BuiltSub = namedtuple('BuildSub', 'image_digest')


def build_image(client, path, dockerfile, no_build, no_cache=False):
    tag = 'myimage'

    if not no_build:
        cmd = ['docker', 'build', '-t', tag, '-f', dockerfile]
        if no_cache:
            cmd.append('--no-cache')
        cmd.append(path)
        subprocess.check_call(cmd)

    image = client.images.get(tag)
    return image


class CouldNotReadSubInfo(Exception):
    pass


def read_submission_info(dirname):
    if not os.path.exists(dirname):
        msg = 'Could not find directory:\n   %s' % dirname
        raise CouldNotReadSubInfo(msg)

    bn = 'submission.yaml'
    fn = os.path.join(dirname, bn)

    if not os.path.exists(fn):
        msg = 'I expected to find the file %s' % fn

        msg += '\n\nThese are the contents of the directory %s:' % dirname
        for x in os.listdir(dirname):
            msg += '\n- %s' % x

        raise CouldNotReadSubInfo(msg)
    contents = open(fn).read()
    try:
        data = yaml.load(contents)
    except BaseException as e:
        raise CouldNotReadSubInfo(traceback.format_exc(e))
    try:
        return SubmissionDescription.from_yaml(data)
    except BaseException as e:
        msg = 'Could not read file %r: %s' % (fn, e)
        raise CouldNotReadSubInfo(msg)
