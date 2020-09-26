import json
import os
import subprocess
import sys


from .cli_common import ChallengeEnvironment
from .cli_submit import dt_challenges_cli_submit

from . import logger

DT1_TOKEN_CONFIG_KEY = "token_dt1"

CONFIG_DOCKER_USERNAME = "docker_username"

__all__ = ["dt_challenges_cli_main"]


def dt_challenges_cli_main():
    args = sys.argv[1:]

    cmds = {"submit": dt_challenges_cli_submit}

    logger.info("env", env=dict(os.environ))

    fn = "/credentials"
    with open(fn) as f:
        c = f.read()
    data = json.loads(c)
    docker_username = data["Username"]
    docker_secret = data["Secret"]

    token = os.environ.get(DT1_TOKEN_CONFIG_KEY)
    # docker_username = os.environ.get(CONFIG_DOCKER_USERNAME)
    environment = ChallengeEnvironment(
        token=token, docker_username=docker_username, docker_secret=docker_secret
    )

    cmd = ["docker", "login", "-u", docker_username, "--password-stdin"]
    subprocess.check_output(cmd, input=docker_secret.encode())

    first = args[0]
    rest = args[1:]

    logger.info(first=first, rest=rest)

    if first in cmds:
        f = cmds[first]
        f(rest, environment)
    else:
        logger.error(f"Cannot find command {first}", args=args)
    sys.exit(2)
