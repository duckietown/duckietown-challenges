from abc import ABCMeta, abstractmethod


class ChallengeEvaluator(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def prepare(self, cie):
        pass

    @abstractmethod
    def score(self, cie):
        pass


class ChallengeScorer(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def score(self, cie):
        pass
