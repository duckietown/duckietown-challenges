__version__ = '0.2.3'

import logging

logging.basicConfig()
dclogger = logging.getLogger('duckietown-challenges')
dclogger.setLevel(logging.DEBUG)

from .challenges_constants import ChallengesConstants
from .solution_interface import *
from .constants import *
from .exceptions import *

from .challenge_evaluator import *
from .challenge_solution import *
from .challenge_results import *
from .cie_concrete import *

from .runner import dt_challenges_evaluator

dclogger.info('duckietown-challenges %s' % __version__)
