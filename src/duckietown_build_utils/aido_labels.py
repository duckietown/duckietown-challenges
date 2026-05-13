import argparse
import json
import os
import platform
import sys
import traceback
from dataclasses import dataclass
from getpass import getuser
from typing import Dict, List, Optional

from duckietown_docker_utils import ENV_REGISTRY
from zuper_commons.logs import setup_logging
from zuper_commons.types import ZException

from . import logger
from .commons import CannotGetDirInfo, get_dir_info

__all__ = ["aido_labels_main", "get_duckietown_labels"]


def get_duckietown_labels(dirname: str) -> Dict[str, str]:
    # now = datetime.now(tz=pytz.utc)
    # timestamp = now.isoformat()

    try:
        di = get_dir_info(dirname)
    except CannotGetDirInfo:
        logger.warning(f"Cannot get repo info from {dirname}")
        return {}

    prefix = f"org.duckietown.label.v3.{di.repo_name}"

    labels = {
        "code.vcs": "git",
        "code.repository": di.repo_name,
        "code.sha": di.sha,
        "code.dirty": str(di.dirty),
        "code.branch": di.branch,
        "code.url": di.vcs_url,
        "code.version.head": di.tag,
        "code.version.closest": di.closest_tag,
        # "build.time": timestamp,
        "build.user": getuser(),
        "build.host": platform.node(),
        "build.arch": platform.machine(),
        "build.platform": platform.platform(),
    }
    vnames = ["PIP_INDEX_URL", ENV_REGISTRY]
    for v in vnames:
        labels[f"env.{v}"] = os.environ.get(v, None)

    try:
        pi = get_project_info(dirname)
    except NotFound:
        pass
    else:
        labels["template.name"] = pi.project_type
        labels["template.version"] = pi.version
    # logger.info(pi=pi)

    labels = {f"{prefix}.{k}": v for k, v in labels.items()}

    return labels


class NotFound(ZException):
    pass


REQUIRED_METADATA_KEYS = {
    "*": ["TYPE_VERSION"],
    "1": ["TYPE", "VERSION"],
    "2": ["TYPE", "VERSION"],
    "3": ["TYPE", "VERSION"],
}


@dataclass
class ProjectInfo:
    project_name: str
    project_type: Optional[str]
    version: Optional[str]


def get_project_info(path: str) -> ProjectInfo:
    project_name = os.path.basename(os.path.abspath(path))
    if not os.path.exists(path):
        raise NotFound(f"Path {path} does not exist.")

    metafile = os.path.join(path, ".dtproject")
    # if the file '.dtproject' is missing
    if not os.path.exists(metafile):
        msg = f"The path '{metafile}' does not appear to be a Duckietown project. "
        msg += "\nThe metadata file '.dtproject' is missing."
        raise NotFound(msg)
    # load '.dtproject'
    with open(metafile, "rt") as metastream:
        metadata_lines = metastream.readlines()
    # empty metadata?
    if not metadata_lines:
        msg = "The metadata file '.dtproject' is empty."
        raise ZException(msg)
    # parse metadata
    lines = [_.strip() for _ in metadata_lines]
    lines = [_ for _ in lines if _]
    try:
        metadata = {p[0].strip().upper(): p[1].strip() for p in [line.split("=") for line in lines]}
    except Exception:
        msg = "Malformed metadatad."
        raise ZException(msg, metafile=metafile, lines=lines)
    # look for version-agnostic keys

    for key in REQUIRED_METADATA_KEYS["*"]:
        if key not in metadata:
            msg = "The metadata file '.dtproject' does not contain the key '%s'." % key
            raise ZException(msg, metadata=metadata)
    # validate version
    version = metadata["TYPE_VERSION"]
    if version == "*" or version not in REQUIRED_METADATA_KEYS:
        msg = "The project version %s is not supported." % version
        raise ZException(msg, metadata=metadata)
    # validate metadata
    for key in REQUIRED_METADATA_KEYS[version]:
        if key not in metadata:
            msg = "The metadata file '.dtproject' does not contain the key '%s'." % key
            raise ZException(msg, metadata=metadata)
    # metadata is valid
    # metadata["NAME"] = project_name
    # metadata["PATH"] = path
    return ProjectInfo(project_name=project_name, project_type=metadata["TYPE"], version=metadata["VERSION"])


def aido_labels_main(args=None):
    setup_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", "-d", default=".")
    # parser.add_argument('--directory', '-d', default=".")
    parsed = parser.parse_args(args)

    # noinspection PyBroadException
    try:
        directory = parsed.directory
        # absdir = os.path.realpath(directory)

        if not os.path.exists(directory):
            sys.exit(-2)

        labels = get_duckietown_labels(directory)
        args = get_build_args_from_labels(labels)

        print(" ".join(args))

    except SystemExit:
        raise
    except BaseException:
        logger.error(traceback.format_exc())
        sys.exit(3)


def get_build_args_from_labels(labels: Dict[str, str]) -> List[str]:
    args = []
    for k, v in labels.items():
        args.append("\n--label")
        x = json.dumps(v)
        # args.append(f'\'{k}={x}\'')
        args.append(f"{k}={x}")
        # args.append(f'{k}:1')
    return args
