import os
from collections import OrderedDict

from .constants import CHALLENGE_RESULTS_YAML, ChallengeResultsStatus
from .yaml_utils import write_yaml, read_yaml_file


class ChallengeResults(object):

    def __init__(self, status, msg, scores, stats=None):
        assert status in ChallengeResultsStatus.ALL, (status, ChallengeResultsStatus.ALL)
        self.status = status
        self.msg = msg
        self.scores = scores
        if stats is None:
            stats = {}
        self.stats = stats

    def to_yaml(self):
        data = {}
        data['status'] = self.status
        data['msg'] = self.msg
        data['scores'] = self.scores
        data['stats'] = self.stats
        return data

    def __repr__(self):
        return 'ChallengeResults(%s)' % self.to_yaml()

    @staticmethod
    def from_yaml(data):
        d0 = dict(**data)
        status = d0.pop('status')
        msg = d0.pop('msg')
        scores = d0.pop('scores')
        stats = d0.pop('stats', {})
        if d0:
            msg = 'Extra fields: %s' % list(d0)
            raise ValueError(msg)

        return ChallengeResults(status, msg, scores, stats)

    def get_status(self):
        return self.status

    def get_stats(self):
        stats = OrderedDict()
        stats['scores'] = self.scores
        stats['msg'] = self.msg
        return stats


def declare_challenge_results(root, cr):
    if root is None:
        root = '/'
    data = cr.to_yaml()
    fn = os.path.join(root, CHALLENGE_RESULTS_YAML)
    write_yaml(data, fn)


def read_challenge_results(root):
    fn = os.path.join(root, CHALLENGE_RESULTS_YAML)
    if not os.path.exists(fn):
        msg = 'File %r does not exist.' % fn
        raise Exception(msg)
    data = read_yaml_file(fn)

    return ChallengeResults.from_yaml(data)
