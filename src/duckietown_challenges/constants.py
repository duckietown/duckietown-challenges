import os

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


class ChallengeResultsStatus(object):
    SUCCESS = 'success'
    FAILED = 'failed'  # the solution failed
    ERROR = 'error'  # there was a problem with the evaluation (but not the solution)

    ERROR_CODE = ERROR
    ERROR_TMP_EVALUATOR = ERROR

    ALL = [SUCCESS, FAILED, ERROR]
    # XXX: to merge



