# coding=utf-8
import os
from collections import OrderedDict

from .challenges_constants import ChallengesConstants
from .constants import CHALLENGE_RESULTS_YAML, DEFAULT_ROOT
from .utils import wrap_config_reader2
from .yaml_utils import write_yaml, read_yaml_file
from typing import *

class ChallengeResults:
    ipfs_hashes: Dict[str, str]

    def __init__(self, status, msg, scores, stats=None, ipfs_hashes: Optional[Dict[str, str]] =None):
        assert status in ChallengesConstants.ALLOWED_JOB_STATUS, \
            (status,  ChallengesConstants.ALLOWED_JOB_STATUS)
        self.status = status
        self.msg = msg
        self.scores = scores
        if stats is None:
            stats = {}
        self.stats = stats
        self.ipfs_hashes = ipfs_hashes or {}

    def to_yaml(self):
        data = {}
        data['status'] = self.status
        data['msg'] = self.msg
        data['scores'] = self.scores
        data['stats'] = self.stats
        data['ipfs_hashes'] = self.ipfs_hashes
        return data

    def __repr__(self):
        return 'ChallengeResults(%s)' % self.to_yaml()

    # noinspection PyArgumentList
    @classmethod
    @wrap_config_reader2
    def from_yaml(cls, d0):
        status = d0.pop('status')
        msg = d0.pop('msg')
        scores = d0.pop('scores')
        stats = d0.pop('stats', {})
        ipfs_hashes = d0.pop('ipfs_hashes', {})
        return ChallengeResults(status, msg, scores, stats, ipfs_hashes)

    def get_status(self):
        return self.status

    def get_stats(self):
        stats = OrderedDict()
        stats['scores'] = self.scores
        stats['msg'] = self.msg
        return stats

from typing import *

def declare_challenge_results(root: Optional[str], cr: ChallengeResults):
    root = root or DEFAULT_ROOT
    data = cr.to_yaml()
    fn = os.path.join(root, CHALLENGE_RESULTS_YAML)
    write_yaml(data, fn)


class NoResultsFound(Exception):
    pass

def read_challenge_results(root):
    fn = os.path.join(root, CHALLENGE_RESULTS_YAML)
    if not os.path.exists(fn):
        msg = 'File %r does not exist.' % fn
        raise NoResultsFound(msg)
    #
    # with open(fn) as f:
    #     contents = f.read()
    #
    # if '!!omap' in contents:
    #     contents = contents.replace('!!omap', '')
    #
    # data = yaml.load(contents, Loader=yaml.Loader)

    data = read_yaml_file(fn)

    return ChallengeResults.from_yaml(data)

