import json
import os
import subprocess
import sys
import traceback

from . import logger
from .cli_common import ChallengeEnvironment
from .cli_submit import dt_challenges_cli_submit
from .exceptions import InvalidEnvironment

DT1_TOKEN_CONFIG_KEY = "token_dt1"
CONFIG_DOCKER_USERNAME = "docker_username"
CONFIG_DOCKER_PASSWORD = "docker_password"

__all__ = ["dt_challenges_cli_main"]


def dt_challenges_cli_main():
    try:
        dt_challenges_cli_main_()
    except SystemExit:
        raise
    except BaseException:
        logger.error(traceback.format_exc())
        sys.exit(32)


def dt_challenges_cli_main_():
    from zuper_commons.logs import setup_logging

    setup_logging()
    args = sys.argv[1:]

    cmds = {"submit": dt_challenges_cli_submit}

    logger.info("env", env=dict(os.environ))

    fn = "/credentials"
    with open(fn) as f:
        c = f.read()
    data = json.loads(c)
    docker_username = data[CONFIG_DOCKER_USERNAME]
    docker_password = data[CONFIG_DOCKER_PASSWORD]
    token = data[DT1_TOKEN_CONFIG_KEY]
    if docker_password is None or docker_username is None:
        msg = "I need docker username and password"
        raise InvalidEnvironment(msg)

    # docker_username = os.environ.get(CONFIG_DOCKER_USERNAME)
    environment = ChallengeEnvironment(
        token=token, docker_username=docker_username, docker_password=docker_password
    )

    cmd = ["docker", "login", "-u", docker_username, "--password-stdin"]
    try:
        subprocess.check_output(cmd, input=docker_password.encode())
    except subprocess.CalledProcessError as e:
        msg = f'Failed to login with username "{docker_username}".'
        raise InvalidEnvironment(msg) from e

    first = args[0]
    rest = args[1:]

    logger.info(first=first, rest=rest)

    if first in cmds:
        f = cmds[first]
        f(rest, environment)
    else:
        logger.error(f"Cannot find command {first}", args=args)
    sys.exit(2)
