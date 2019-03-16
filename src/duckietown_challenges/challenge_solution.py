# coding=utf-8
from abc import ABCMeta, abstractmethod


class ChallengeSolution(metaclass=ABCMeta):

    @abstractmethod
    def run(self, cie):
        pass
