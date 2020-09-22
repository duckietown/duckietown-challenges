# coding=utf-8
__version__ = "6.0.13"

from zuper_commons.logs import ZLogger

dclogger = logger = ZLogger(__name__)
logger.info(f"version: {__version__}")

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

from .make_readmes import make_readmes_main as make_readmes_main
from .make_readme_templates import make_readmes_templates_main
