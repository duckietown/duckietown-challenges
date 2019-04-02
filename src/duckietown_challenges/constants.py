# coding=utf-8
import os

DEFAULT_ROOT = '/challenges'

# In the end, the evaluator must create this file
CHALLENGE_RESULTS_DIR = 'challenge-results'
CHALLENGE_RESULTS_YAML = os.path.join(CHALLENGE_RESULTS_DIR, 'challenge_results.yaml')

# Example content of the file:
#
# !!omap
# - status: success
# - msg: null
# - scores:
#     lf: 91.09225459488937


# Folder for the output of the solution
CHALLENGE_SOLUTION_OUTPUT_DIR = 'challenge-solution-output'
CHALLENGE_EVALUATION_OUTPUT_DIR = 'challenge-evaluation-output'
CHALLENGE_DESCRIPTION_DIR = 'challenge-description'
CHALLENGE_TMP_SUBDIR = 'tmp'

CHALLENGE_PREVIOUS_STEPS_DIR = 'previous-steps'

# File to be created by the solution, which also signals
# the termination of the run
CHALLENGE_SOLUTION_OUTPUT_YAML = os.path.join(CHALLENGE_SOLUTION_OUTPUT_DIR, 'output-solution.yaml')
CHALLENGE_EVALUATION_OUTPUT_YAML = os.path.join(CHALLENGE_EVALUATION_OUTPUT_DIR, 'output-evaluation.yaml')
CHALLENGE_SOLUTION_DIR = 'challenge-solution'
CHALLENGE_EVALUATION_DIR = 'challenge-evaluation'
CHALLENGE_DESCRIPTION_YAML = os.path.join(CHALLENGE_DESCRIPTION_DIR, 'description.yaml')

ENV_CHALLENGE_NAME = 'challenge_name'
ENV_CHALLENGE_STEP_NAME = 'challenge_step_name'

#
# class ChallengeResultsStatus(object):
#     SUCCESS = 'success'
#     FAILED = 'failed'  # the solution failed
#     ERROR = 'error'  # there was a problem with the evaluation code (but not the solution). Definitive.
#     ERROR_TMP_EVALUATOR = 'host-error' # there was a problem with the host (e.g. ownloading.) Try again!
#     ABORTED = 'aborted' # interrupted by user
#
#     ERROR_CODE = ERROR
#     ALL = [SUCCESS, FAILED, ERROR, ABORTED, ERROR_TMP_EVALUATOR]
#     # XXX: to merge


DEFAULT_DTSERVER = 'https://challenges.duckietown.org/v4'


class Storage(object):
    done = False


def get_duckietown_server_url():
    V = 'DTSERVER'

    if V in os.environ:
        use = os.environ[V]
        if not Storage.done:
            if use != DEFAULT_DTSERVER:
                msg = 'Using server %s instead of default %s' % (use, DEFAULT_DTSERVER)
                from . import dclogger
                dclogger.info(msg)
            Storage.done = True
        return use
    else:
        return DEFAULT_DTSERVER
