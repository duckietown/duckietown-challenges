# coding=utf-8
__version__ = "6.1.19"

from subprocess import CalledProcessError, check_output


def check_no_incompatible():
    cmd = ["pip3", "list"]
    try:
        res = check_output(cmd)
    except FileNotFoundError:
        msg = f"Cannot execute the command {cmd}"
        sys.stderr.write(msg)
    except CalledProcessError:
        tb = traceback.format_exc()
        msg = f"Cannot get list of installed packages:\n\n{tb}"
        sys.stderr.write(msg)
    else:
        packages = res.decode().split()
        forbidden = [
            "duckietown-challenges",
            "zuper-commons-z5",
        ]
        for f in forbidden:
            if f in packages:
                msg = f"""
                    Found incompatible package "{f}" installed.

                    Please uninstall using

                        pip uninstall "{f}"

                """
                sys.stderr.write(msg)
                raise ValueError(msg)


check_no_incompatible()

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
