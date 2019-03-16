# coding=utf-8
from abc import ABCMeta, abstractmethod


class ChallengeEvaluator(metaclass=ABCMeta):

    @abstractmethod
    def prepare(self, cie):
        pass

    @abstractmethod
    def score(self, cie):
        pass


class ChallengeScorer(metaclass=ABCMeta):

    @abstractmethod
    def score(self, cie):
        pass
