import argparse
import os
import subprocess
import sys
import traceback

from zuper_commons.logs import setup_logging

from . import logger
from .commons import get_dir_info

__all__ = ["aido_check_tagged_main"]


def aido_check_tagged_main(args=None):
    if "DT_IGNORE_UNTAGGED" in os.environ:
        return

    setup_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", "-d", default=".")
    parser.add_argument("cmd", nargs="*")
    parsed = parser.parse_args(args)

    # noinspection PyBroadException
    try:
        directory = parsed.directory
        absdir = os.path.realpath(directory)
        rest = parsed.cmd

        if not os.path.exists(directory):
            sys.exit(-2)

        di = get_dir_info(directory)

        if di.tag is None:
            logger.error("This is not tagged. ", directory=absdir, di=di, rest=" ".join(rest))
            sys.exit(1)

        else:
            # logger.info('This is tagged. ',
            #              directory=absdir, di=di, rest=" ".join(rest))
            if rest:
                res = subprocess.run(rest, cwd=directory)
                sys.exit(res.returncode)
            else:
                sys.exit(0)

    except SystemExit:
        raise
    except BaseException:
        logger.error(traceback.format_exc())
        sys.exit(3)
