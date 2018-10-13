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
    bn = 'submission.yaml'
    fn = os.path.join(dirname, bn)

    try:
        data = yaml.load(open(fn).read())
    except Exception as e:
        raise CouldNotReadSubInfo(traceback.format_exc(e))
    try:
        return SubmissionDescription.from_yaml(data)
    except Exception as e:
        msg = 'Could not read file %r: %s' % (fn, e)
        raise CouldNotReadSubInfo(msg)

#
# class SubmissionInfo(object):
#     def __init__(self, challenge_name, user_label, user_payload, protocols, description):
#         self.challenge_name = challenge_name
#         self.user_label = user_label
#         self.user_payload = user_payload
#         self.protocols = protocols
#         self.description = description
#
#     @staticmethod
#     def from_yaml(data):
#         try:
#             if not isinstance(data, dict):
#                 raise Exception("expected dict")
#             data = dict(**data)
#             challenge_name = data.pop('challenge')
#             protocols = data.pop('protocol')
#             if isinstance(protocols, (str, unicode)):
#                 protocols = [protocols]
#             user_label = data.pop('user-label', None)
#             user_payload = data.pop('user-payload', None)
#             description = data.pop('description', None)
#             if data:
#                 msg = 'Unknown keys: %s' % list(data)
#                 raise Exception(msg)
#             return SubmissionInfo(challenge_name, user_label, user_payload, protocols, description)
#         except BaseException as e:
#             msg = 'Could not read submission info: %s' % e
#             raise CouldNotReadSubInfo(msg)
