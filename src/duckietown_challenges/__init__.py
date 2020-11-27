# coding=utf-8
__version__ = "7.0.0"

from zuper_commons.logs import ZLogger

dclogger = logger = ZLogger(__name__)
logger.debug(f"duckietown_challenges version: {__version__}")

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
from .follow import *
from .rest_methods import *
