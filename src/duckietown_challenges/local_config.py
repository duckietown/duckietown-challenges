# coding=utf-8
import os

from .yaml_utils import read_yaml_file


class ChallengeInfoLocal:
    def __init__(self, challenge_name):
        self.challenge_name = challenge_name


def read_challenge_info(dirname):
    bn = 'challenge.yaml'
    fn = os.path.join(dirname, bn)

    data = read_yaml_file(fn)
    try:
        challenge_name = data['challenge']

        return ChallengeInfoLocal(challenge_name)
    except BaseException as e:
        msg = 'Could not read file %r: %s' % (fn, e)
        raise Exception(msg)
