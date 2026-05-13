import argparse
import os
import subprocess
import sys
import traceback
from typing import List

from zuper_commons.text.zc_wildcards import expand_wildcard

from . import logger
from .commons import DirInfo, get_dir_info

__all__ = ["aido_check_not_dirty_main", "get_dir_info_exceptions"]


def aido_check_not_dirty_main(args=None):
    if "DT_IGNORE_DIRTY" in os.environ:
        return
    # logger.info(e=dict(os.environ))

    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", "-d", default=".")
    parser.add_argument("cmd", nargs="*")
    parsed = parser.parse_args(args)
    # logger.error(f"check-not-dirty", parsed=parsed)

    # noinspection PyBroadException
    try:
        directory = parsed.directory
        absdir = os.path.realpath(directory)

        rest = parsed.cmd

        if not os.path.exists(absdir):
            logger.error(f"The directory does not exist: {absdir}")
            sys.exit(4)

        di = get_dir_info_exceptions(directory)

        if di.dirty:
            logger.error("The directory is dirty.", absdir=absdir, di=di, rest=" ".join(rest))
            sys.exit(1)

        else:
            # logger.info("This is not dirty.", directory=directory, di=di, rest=" ".join(rest))

            if rest:
                try:
                    subprocess.check_call(rest, cwd=directory)
                except subprocess.CalledProcessError as e:
                    logger.error(stderr=e.stderr, stdout=e.stdout)
                    # sys.exit(e.returncode)
            else:
                # logger.info("nothing to do")
                sys.exit(0)

    except SystemExit:

        raise
    except:
        logger.error(traceback.format_exc())
        sys.exit(3)


def get_dir_info_exceptions(directory: str) -> DirInfo:
    di = get_dir_info(directory)
    absdir = os.path.realpath(directory)
    setup = os.path.join(absdir, "setup.py")
    if os.path.exists(setup):
        # if python package, we only care about python files
        allchanges = di.modified + di.deleted + di.added
        # + di.untracked

        pyfiles = [_ for _ in allchanges if _.endswith(".py")]
        others = [_ for _ in allchanges if not _.endswith(".py")]
        py_dirty = len(pyfiles) > 0

        if (not py_dirty) and di.dirty:
            if others:
                msg = "Python package detected. Ignoring non-python file changes."
                logger.info(msg, ignored=others)
        di.dirty = py_dirty
    else:
        allchanges = di.modified + di.deleted + di.added
        allchanges = remove_to_ignore(allchanges)
        # logger.info(allchanges=allchanges)

        di.dirty = len(allchanges) > 0
    return di


def remove_to_ignore(a: List[str]) -> List[str]:
    to_remove = ["*.resolved", ".gitignore", "Makefile"]
    for i in to_remove:
        try:
            no = expand_wildcard(i, a)
        except ValueError:
            no = []
        else:
            logger.info(f"ignoring {a!r} because {i!r}")
        no.append(i)
        # logger.info(f" {i!r}  -> {no}")
        a = [_ for _ in a if _ not in no]
    return a
