__version__ = '3.0.40'

import logging

logging.basicConfig()
dclogger = logging.getLogger('duckietown-challenges')
dclogger.setLevel(logging.DEBUG)
dclogger.info('duckietown-challenges %s' % __version__)

from .challenges_constants import ChallengesConstants
from .solution_interface import *
from .constants import *
from .exceptions import *

from .challenge_evaluator import *
from .challenge_solution import *
from .challenge_results import *
from .cie_concrete import *

from .runner import dt_challenges_evaluator

from .make_readmes import make_readmes_main as make_readmes_main
from .make_readme_templates import make_readmes_templates_main
from .runner_local import runner_local_main
