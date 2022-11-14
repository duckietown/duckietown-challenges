# coding=utf-8
__version__ = "6.3.32"

from zuper_commons.logs import ZLogger

logger = ZLogger(__name__)
import os

path = os.path.dirname(os.path.dirname(__file__))

logger.debug(f"duckietown_challenges version {__version__} path {path}")

from .types import *
from .rest import *
from .challenges_constants import ChallengesConstants
from .solution_interface import *
from .constants import *
from .exceptions import *
from .challenge import *
from .challenge_evaluator import *
from .challenge_solution import *
from .challenge_results import *
from .cie_concrete import *
from .rest_methods import *
from .submission_read import *
