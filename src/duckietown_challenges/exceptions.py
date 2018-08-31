
class ChallengeException(Exception):
    pass


class NotAvailable(ChallengeException):
    pass


class InvalidConfiguration(ChallengeException):
    pass


class InvalidSubmission(Exception):
    """ Can be raised by evaluator """
    pass

