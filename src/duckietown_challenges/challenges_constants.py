# coding=utf-8
class ChallengesConstants:
    # status for evaluation jobs
    STATUS_JOB_TIMEOUT = 'timeout'
    STATUS_JOB_EVALUATION = 'evaluating'
    STATUS_JOB_FAILED = 'failed'  # submission failed
    STATUS_JOB_ERROR = 'error'  # evaluation failed
    STATUS_JOB_HOST_ERROR = 'host-error'  # evaluation failed
    STATUS_JOB_SUCCESS = 'success'
    STATUS_JOB_ABORTED = 'aborted'

    ALLOWED_JOB_STATUS = [
        STATUS_JOB_EVALUATION,
        STATUS_JOB_SUCCESS,
        STATUS_JOB_TIMEOUT,
        STATUS_JOB_FAILED,
        STATUS_JOB_ERROR,
        STATUS_JOB_ABORTED,
        STATUS_JOB_HOST_ERROR
    ]

    # JOB_TIMEOUT_MINUTES = 30

    DEFAULT_DTSERVER = 'https://challenges.duckietown.org/v4'
    DEFAULT_TIMEOUT = 5

    class Endpoints:
        challenge_define = '/challenge-define'
        registry_info = '/api/registry-info'
        user_info = '/api/user-info'
        submissions = '/api/submissions'
        components = '/api/components'
        challenges = '/api/challenges'
        take_submission = '/api/take-submission'
        auth = '/api/auth'
        reset_submission = '/api/reset-submission'
        change_user_priority = '/api/change-user-priority'
        change_admin_priority = '/api/change-admin-priority'
        reset_job = '/api/reset-job'
        submissions_list = '/api/submissions-list'
        submission_single = '/api/submission-single'
        sub_by_challenges = '/api/sub-by-challenges'

        jobs_by_submission = '/api/jobs-by-submission'
        leaderboards_data = '/api/leaderboardds-data'

    SUBMISSION_CONTAINER_TAG = 'SUBMISSION_CONTAINER'
