import os
from collections import OrderedDict

from .constants import CHALLENGE_RESULTS_YAML, ChallengeResultsStatus
from .yaml_utils import write_yaml, read_yaml_file


class ChallengeResults(object):

    def __init__(self, status, msg, scores):
        assert status in ChallengeResultsStatus.ALL, (status, ChallengeResultsStatus.ALL)
        self.status = status
        self.msg = msg
        self.scores = scores

    def to_yaml(self):
        data = OrderedDict()
        data['status'] = self.status
        data['msg'] = self.msg
        data['scores'] = self.scores
        return data

    def __repr__(self):
        return 'ChallengeResults(%r, %r, %r)' % (self.status, self.msg, self.scores)

    @staticmethod
    def from_yaml(data):
        status = data['status']
        msg = data['msg']
        scores = data['scores']
        return ChallengeResults(status, msg, scores)

    def get_status(self):
        return self.status

    def get_stats(self):
        stats = OrderedDict()
        stats['scores'] = self.scores
        stats['msg'] = self.msg
        return stats

    # def merge(self, cr2):
    #     status = cr2.status
    #     msg = cr2.msg
    #     scores = dict()
    #     scores.update(self.scores)
    #     for k, v in cr2.scores.items():
    #         if k in scores:
    #             msg = 'Warning: step overwrites score %s = %s with %s ' % (k, scores[k], v)
    #             dclogger.warning(msg)
    #     return ChallengeResults(status, msg, scores)



def declare_challenge_results(root, cr):
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
