
class ChallengesConstants(object):
    # status for submission
    STATUS_SUBMITTED = 'submitted'
    STATUS_RETIRED = 'retired'
    STATUS_EVALUATION = 'evaluating'
    STATUS_ABORTED = 'aborted'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_ERROR = 'error'

    ALLOWED_SUB_STATUS = [
        STATUS_SUBMITTED,
        STATUS_RETIRED,
        STATUS_EVALUATION,
        STATUS_ABORTED,
        STATUS_SUCCESS,
        STATUS_FAILED,
        STATUS_ERROR,
    ]

    # status for evaluation jobs
    STATUS_JOB_TIMEOUT = 'timeout'
    STATUS_JOB_EVALUATION = 'evaluating'
    STATUS_JOB_FAILED = 'failed'  # submission failed
    STATUS_JOB_ERROR = 'error'  # evaluation failed
    STATUS_JOB_SUCCESS = 'success'
    STATUS_JOB_ABORTED = 'aborted'

    ALLOWED_JOB_STATUS = [
        STATUS_JOB_TIMEOUT,
        STATUS_JOB_EVALUATION,
        STATUS_JOB_FAILED,
        STATUS_JOB_SUCCESS,
        STATUS_JOB_ERROR,
        STATUS_JOB_ABORTED
    ]
