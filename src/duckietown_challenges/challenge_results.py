# coding=utf-8
import os
from collections import OrderedDict
from typing import Dict, Optional

from . import dclogger
from .challenges_constants import ChallengesConstants, JobStatusString
from .constants import CHALLENGE_RESULTS_YAML, DEFAULT_ROOT
from .utils import wrap_config_reader2
from .yaml_utils import read_yaml_file, write_yaml

__all__ = ["ChallengeResults", "declare_challenge_results", "read_challenge_results", "NoResultsFound"]


class ChallengeResults:
    ipfs_hashes: Dict[str, str]
    msg: Optional[str]
    status: JobStatusString

    def __init__(
        self,
        status: JobStatusString,
        msg: Optional[str],
        scores,
        stats: Optional[dict] = None,
        ipfs_hashes: Optional[Dict[str, str]] = None,
    ):
        assert status in ChallengesConstants.ALLOWED_JOB_STATUS, (
            status,
            ChallengesConstants.ALLOWED_JOB_STATUS,
        )
        self.status = status
        self.msg = msg
        self.scores = scores
        if stats is None:
            stats = {}
        self.stats = stats
        self.ipfs_hashes = ipfs_hashes or {}

    def to_yaml(self):
        data = {}
        data["status"] = self.status
        data["msg"] = self.msg
        data["scores"] = self.scores
        data["stats"] = self.stats
        data["ipfs_hashes"] = self.ipfs_hashes
        return data

    def __repr__(self):
        return "ChallengeResults(%s)" % self.to_yaml()

    # noinspection PyArgumentList
    @classmethod
    @wrap_config_reader2
    def from_yaml(cls, d0):
        status = d0.pop("status")
        msg = d0.pop("msg")
        scores = d0.pop("scores")
        stats = d0.pop("stats", {})
        ipfs_hashes = d0.pop("ipfs_hashes", {})
        return ChallengeResults(status, msg, scores, stats, ipfs_hashes)

    def get_status(self):
        return self.status

    def get_stats(self):
        stats = OrderedDict()
        stats["scores"] = self.scores
        stats["msg"] = self.msg
        return stats


def declare_challenge_results(root: Optional[str], cr: ChallengeResults):
    root = root or DEFAULT_ROOT
    data = cr.to_yaml()
    fn = os.path.join(root, CHALLENGE_RESULTS_YAML)
    write_yaml(data, fn)
    msg = f"Just wrote the challenge result to {fn}"
    dclogger.info(msg, data=data)


class NoResultsFound(Exception):
    pass


def read_challenge_results(root: str) -> ChallengeResults:
    fn = os.path.join(root, CHALLENGE_RESULTS_YAML)
    if not os.path.exists(fn):
        msg = "File %r does not exist." % fn
        raise NoResultsFound(msg)
    data = read_yaml_file(fn)

    return ChallengeResults.from_yaml(data)
