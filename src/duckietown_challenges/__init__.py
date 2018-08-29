__version__ = '0.1.8'

import logging

logging.basicConfig()
dclogger = logging.getLogger('duckietown_challenges')
dclogger.setLevel(logging.DEBUG)
import os

CHALLENGE_SOLUTION_OUTPUT = '/challenge-solution-output'
CHALLENGE_EVALUATION_OUTPUT = '/challenge-evaluation-output'
CHALLENGE_SOLUTION = '/challenge-solution'
CHALLENGE_EVALUATION = '/challenge-evaluation'
CHALLENGE_DESCRIPTION = '/challenge-description'
CONFIG_LOCATION = os.path.join(CHALLENGE_DESCRIPTION, 'description.yaml')
OUTPUT_JSON = 'output.json'

from .runner import dt_challenges_evaluator
from .solution_interface import *

print('duckietown-challenges version %s' % __version__)
