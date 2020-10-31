# coding=utf-8
from zuper_commons.types import ZException


class ChallengeException(ZException):
    pass


class NotAvailable(ChallengeException):
    pass


class InvalidConfiguration(ChallengeException):
    pass


class InvalidSubmission(ZException):
    """ Can be raised by evaluator """

    pass


class InvalidEvaluator(ZException):
    pass


class InvalidEnvironment(ZException):
    pass


class AbortedByUser(ZException):
    pass
