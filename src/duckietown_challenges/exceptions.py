# coding=utf-8
class ChallengeException(Exception):
    pass


class NotAvailable(ChallengeException):
    pass


class InvalidConfiguration(ChallengeException):
    pass


class InvalidSubmission(Exception):
    """ Can be raised by evaluator """
    pass


class InvalidEvaluator(Exception):
    pass

class InvalidEnvironment(Exception):
    pass

class AbortedByUser(Exception):
    pass

