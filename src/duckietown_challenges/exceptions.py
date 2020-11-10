# coding=utf-8
from zuper_commons.types import ZException


class ChallengeException(ZException):
    pass


class NotAvailable(ChallengeException):
    pass


class InvalidConfiguration(ChallengeException):
    pass


class InvalidSubmission(ChallengeException):
    """ Can be raised by evaluator """

    pass


class InvalidEvaluator(ChallengeException):
    pass


class InvalidEnvironment(ChallengeException):
    pass


class AbortedByUser(ChallengeException):
    pass


class AbortedByServer(ChallengeException):
    pass
