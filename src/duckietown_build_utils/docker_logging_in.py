from typing import Set, Tuple

import docker
from zuper_commons.types import ZException
from docker.errors import APIError
from . import logger
from .buildresult import parse_complete_tag
from .credentials import DockerCredentials
from .types import DockerCompleteImageName, DockerRegistryName, DockerSecret, DockerUsername

__all__ = ["DockerLoginError", "docker_login", "do_login_for_registry", "do_login_for_image"]


class DockerLoginError(ZException):
    pass


class LoggedInStorage:
    done: Set[Tuple[DockerRegistryName, DockerUsername]] = set()


def docker_login(
    client: docker.DockerClient,
    registry: DockerRegistryName,
    docker_username: DockerUsername,
    docker_password: DockerSecret,
):
    k = registry, docker_username
    if k in LoggedInStorage.done:
        pass
        # logger.debug(f"Already logged as {docker_username!r} to {registry}")
        # logger.warn(f'we will do it again {docker_password!r}')
    LoggedInStorage.done.add(k)
    # client = docker.from_env()
    try:
        client.login(username=docker_username, password=docker_password, reauth=True, registry=registry)
    except APIError as e:
        if "andrea" in docker_username:
            pwd = f"using password {docker_password!r}"
        else:
            pwd = ""
        raise DockerLoginError(f"Could not login to {registry!r} as {docker_username!r} {pwd}") from e


def do_login_for_image(
    client: docker.DockerClient, credentials: DockerCredentials, im: DockerCompleteImageName
):
    if im is None:
        raise ValueError("im is None")
    try:
        br = parse_complete_tag(im)
        do_login_for_registry(client, credentials, br.registry)
    except Exception as e:
        msg = f"Could not log in for image {im!r}"
        raise Exception(msg) from e


def do_login_for_registry(
    client: docker.DockerClient, credentials: DockerCredentials, registry: DockerRegistryName
):
    if registry is None:
        raise ValueError("registry is None")
    if registry in credentials:
        docker_login(client, registry, credentials[registry]["username"], credentials[registry]["secret"])
    else:
        logger.warn(f"No credentials to login to registry {registry!r}", known=list(credentials))
