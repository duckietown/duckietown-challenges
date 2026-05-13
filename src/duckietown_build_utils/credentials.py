from typing import Dict, TypedDict

from .types import DockerRegistryName, DockerUsername, DockerSecret

__all__ = ["DockerCredentials", "Credential"]


class Credential(TypedDict):
    username: DockerUsername
    secret: DockerSecret


DockerCredentials = Dict[DockerRegistryName, Credential]
