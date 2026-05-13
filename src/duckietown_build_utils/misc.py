import os
import platform
from typing import Dict, List

from duckietown_docker_utils import ENV_REGISTRY, IMPORTANT_ENVS
from . import logger

__all__ = ["get_important_env_build_args_dict", "get_important_env_build_args"]

CANONICAL_ARCH = {
    "arm": "arm32v7",
    "arm32v7": "arm32v7",
    "armv7l": "arm32v7",
    "armhf": "arm32v7",
    "x64": "amd64",
    "x86_64": "amd64",
    "amd64": "amd64",
    "Intel 64": "amd64",
    "arm64": "arm64v8",
    "arm64v8": "arm64v8",
    "armv8": "arm64v8",
    "aarch64": "arm64v8",
}


def get_important_env_build_args_dict(dockerfile_content: str) -> Dict[str, str]:
    args = {}
    for vname, default_value in IMPORTANT_ENVS.items():
        if vname in dockerfile_content:
            value = os.environ.get(vname, default_value)
            args[vname] = value

    machine = platform.machine()
    if machine not in CANONICAL_ARCH:
        msg = f"Unknown machine {machine!r}. Known: {list(CANONICAL_ARCH)}"
        logger.warn(msg)
    else:
        args["ARCH"] = CANONICAL_ARCH[machine]
    # Put it always
    if ENV_REGISTRY not in args:
        args[ENV_REGISTRY] = os.environ.get(ENV_REGISTRY, IMPORTANT_ENVS[ENV_REGISTRY])

    # args["AIDO_REGISTRY"] = args[ENV_REGISTRY]  # OLD support
    return args


def get_important_env_build_args(dockerfile_content: str) -> List[str]:
    ds = get_important_env_build_args_dict(dockerfile_content)
    args = []
    for k, v in ds.items():
        args.extend(["--build-arg", f"{k}={v}"])
    return args
