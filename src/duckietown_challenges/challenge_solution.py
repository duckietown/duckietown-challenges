# coding=utf-8
from abc import ABCMeta, abstractmethod


class ChallengeSolution(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def run(self, cie):
        pass
