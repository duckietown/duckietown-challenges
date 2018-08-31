from collections import OrderedDict

import os
from .yaml_utils import write_yaml, read_yaml_file
from .constants import CHALLENGE_RESULTS_YAML



class ChallengeResults(object):

    def __init__(self, status, msg, scores):
        self.status = status
        self.msg = msg
        self.scores = scores


    def to_yaml(self):
        data = OrderedDict()
        data['status'] = self.status
        data['msg'] = self.msg
        data['scores'] = self.scores
        return data

    @staticmethod
    def from_yaml(data):
        status = data['status']
        msg = data['msg']
        scores = data['scores']
        return ChallengeResults(status, msg, scores)


def declare_challenge_results(root, cr):
    data = cr.to_yaml()

    fn = os.path.join(root, CHALLENGE_RESULTS_YAML)
    write_yaml(data, fn)


def read_challenge_results(root):
    fn = os.path.join(root, CHALLENGE_RESULTS_YAML)

    data = read_yaml_file(fn)

    return ChallengeResults.from_yaml(data)
