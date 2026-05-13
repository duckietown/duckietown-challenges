# coding=utf-8
__version__ = "6.5.2"

from zuper_commons.logs import ZLogger

logger = ZLogger(__name__)
import os

path = os.path.dirname(os.path.dirname(__file__))

logger.debug(f"duckietown_challenges version {__version__} path {path}")

from .challenge import *
from .challenge_evaluator import *
from .challenge_results import *
from .challenge_solution import *
from .challenges_constants import ChallengesConstants
from .cie_concrete import *
from .constants import *
from .docker_support import *
from .exceptions import *
from .rest import *
from .rest_methods import *
from .solution_interface import *
from .submission_read import *
from .types import *
