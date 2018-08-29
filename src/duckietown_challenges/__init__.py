__version__ = '0.1.6'

CHALLENGE_SOLUTION_OUTPUT = '/challenge-solution-output'
CHALLENGE_EVALUATION_OUTPUT = '/challenge-evaluation-output'
CHALLENGE_SOLUTION = '/challenge-solution'
CHALLENGE_EVALUATION = '/challenge-evaluation'
CONFIG_LOCATION = '/challenge/description.yaml'
OUTPUT_JSON = 'output.json'


from .runner import dt_challenges_evaluator
from .solution_interface import *
