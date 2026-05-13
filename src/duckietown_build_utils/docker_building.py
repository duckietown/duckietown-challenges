import json
import os
import sys
import time
import traceback

import docker
from docker import DockerClient
from docker.errors import APIError
from zuper_commons.types import ZException
from .credentials import DockerCredentials

from . import logger

from .dockerfile_utils import get_resolved_from
from .docker_logging_in import do_login_for_image

__all__ = ["run_build", "BuildFailed", "log_in_for_build"]


class BuildFailed(ZException):
    pass


def log_in_for_build(client: docker.DockerClient, dockerfile_contents: str, credentials: DockerCredentials):
    for x in get_resolved_from(dockerfile_contents):
        do_login_for_image(client, credentials, x)


def run_build(client: DockerClient, rm=True, **kwargs):
    """ """
    # logger.debug(json.dumps(kwargs, indent=2))
    while True:
        try:
            run_build_(client, rm=rm, **kwargs)
        except BuildFailed as e:
            s = str(e)
            if "net/http" in s or "i/o" in s:
                logger.error("looks like it failed because of network; retrying.")
                time.sleep(2)
            else:
                raise
        else:
            break


def run_build_(client: DockerClient, **kwargs):
    """Raises BuildFailed"""
    # logger.debug("now running build", cwd=os.getcwd(), kwargs=kwargs)
    try:
        logger.debug("Running build... [silence is docker creating the context]")
        for line in client.api.build(**kwargs, decode=True):
            # logger.debug(line=line)
            line = _build_line(line)
            if line is not None:
                sys.stderr.write(line)
            sys.stderr.flush()

    except APIError as e:
        logger.error(traceback.format_exc())
        msg = "An error occurred while building the project image."
        raise BuildFailed(msg, kwargs=kwargs) from e
    except ProjectBuildError as e:
        logger.error(traceback.format_exc())
        se = str(e)
        timeout = "Client.Timeout" in se or "i/o timeout" in se
        if timeout:
            msg = f"Docker timeout while building the image:\n{e}"
            raise BuildFailed(msg) from None

        msg = f"An error occurred while building the project image."
        raise BuildFailed(msg, kwargs=kwargs) from e
    except:
        logger.error(traceback.format_exc())
        raise
    finally:
        sys.stderr.flush()


class ProjectBuildError(ZException):
    pass


def _build_line(line: dict):
    # logger.info(line=line)
    if "error" in line and "errorDetail" in line:
        msg = line["errorDetail"]["message"]
        logger.error(msg)
        raise ProjectBuildError(msg)
    if "status" in line:
        # logger.info(line['status'])
        return line["status"]
    if "stream" not in line:
        return None
    line = line["stream"].strip("\n")
    if not line:
        return None
    # this allows apps inside docker build to clear lines
    if not line.endswith("\r"):
        line += "\n"
    # ---
    return line
