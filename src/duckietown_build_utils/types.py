from typing import NewType

__all__ = [
    "DockerRegistryName",
    "DockerOrganizationName",
    "DockerRepositoryName",
    "DockerTag",
    "DockerImageDigest",
    "DockerCompleteImageName",
    "DockerUsername",
    "DockerImageID",
    "DockerSecret",
]

DockerRegistryName = NewType("DockerCompleteImageName", str)

DockerOrganizationName = NewType("DockerOrganizationName", str)
DockerRepositoryName = NewType("DockerRepositoryName", str)
DockerTag = NewType("DockerTag", str)
DockerImageDigest = NewType("DockerImageDigest", str)

DockerImageID = NewType("DockerImageID", str)
DockerCompleteImageName = NewType("DockerCompleteImageName", str)
DockerUsername = NewType("DockerUsername", str)
DockerSecret = NewType("DockerSecret", str)
