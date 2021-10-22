# coding=utf-8
from abc import ABC, abstractmethod

__all__ = ["ChallengeEvaluator", "ChallengeScorer"]


class ChallengeEvaluator(ABC):
    @abstractmethod
    def prepare(self, cie):
        pass

    @abstractmethod
    def score(self, cie):
        pass


class ChallengeScorer(ABC):
    @abstractmethod
    def score(self, cie):
        pass
