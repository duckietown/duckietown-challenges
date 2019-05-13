# coding=utf-8
__version__ = '4.0.26'
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

from .make_readmes import make_readmes_main as make_readmes_main
from .make_readme_templates import make_readmes_templates_main

