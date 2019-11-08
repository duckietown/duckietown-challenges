# coding=utf-8
from abc import ABCMeta, abstractmethod

__all__ = ["ChallengeSolution"]


class ChallengeSolution(metaclass=ABCMeta):
    @abstractmethod
    def run(self, cie):
        pass
