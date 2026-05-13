from dataclasses import dataclass
from typing import cast, Optional

from zuper_commons.types import check_isinstance, ZValueError

from .types import (
    DockerCompleteImageName,
    DockerImageDigest,
    DockerOrganizationName,
    DockerRegistryName,
    DockerRepositoryName,
    DockerTag,
)

__all__ = ["BuildResult", "parse_complete_tag", "get_complete_tag", "get_complete_tag_notag"]


@dataclass
class BuildResult:
    registry: Optional[DockerRegistryName]
    organization: DockerOrganizationName
    repository: DockerRepositoryName
    tag: Optional[DockerTag]
    digest: Optional[DockerImageDigest]

    def __post_init__(self):
        if self.repository:
            assert not "@" in self.repository, self
        if self.tag:
            assert not "@" in self.tag, self

        if self.digest is not None:
            if not self.digest.startswith("sha256"):
                msg = "Unknown digest format: %s " % self.digest
                raise ValueError(msg)
            if self.digest.startswith("sha256:sha256"):
                msg = "What happened here? %s " % self.digest
                raise ValueError(msg)


# localhost:5000/andreacensi/aido2_simple_prediction_r1-step1-simulation-evaluation:2019_04_03_20_03_28@sha256
# :9c1ed66dc31ad9f1b6e454448f010277e38edf051f15b56ff985ec4292290614


DEFAULT_REGISTRY = cast(DockerRegistryName, "docker.io")


def parse_complete_tag(x: DockerCompleteImageName) -> BuildResult:
    """ """
    check_isinstance(x, str)
    ns = x.count("/")
    if ns == 2:
        registry, rest = x.split("/", maxsplit=1)

    elif ns == 1 or ns == 0:
        registry = DEFAULT_REGISTRY
        rest = x
    else:
        msg = "Could not parse complete tag"
        raise ZValueError(msg, x=x)

    nsha = rest.count("@")
    if nsha:
        rest, digest = rest.split("@")
        if not digest.startswith("sha256"):
            msg = "Unknown digest format: %s for %s" % (digest, x)
            raise ValueError(msg)
    else:
        digest = None

    n = rest.count(":")
    if n:
        org_repo, tag = rest.split(":", maxsplit=1)
    else:
        org_repo = rest
        tag = None

    if org_repo.count("/") == 0:
        organization = "library"
        repository = org_repo
    elif org_repo.count("/") == 1:  # XXX
        organization, repository = org_repo.split("/")
    else:
        raise ValueError((x, rest, org_repo))
    if repository != repository.lower():
        msg = f"Repository name must be lowercase: found {repository!r} in {x!r}."
        raise ValueError(msg)

    try:
        return BuildResult(
            registry=registry,
            organization=organization,
            repository=repository,
            tag=tag,
            digest=digest,
        )
    except ValueError as e:
        raise ValueError(x) from e


def get_complete_tag(br: BuildResult) -> DockerCompleteImageName:
    complete = f"{br.organization}/{br.repository}"
    if br.tag:
        complete += f":{br.tag}"
    if br.registry and br.registry != DEFAULT_REGISTRY:
        complete = f"{br.registry}/{complete}"
    if br.digest:
        complete += f"@{br.digest}"
    return DockerCompleteImageName(complete)


def get_complete_tag_notag(br: BuildResult) -> DockerCompleteImageName:
    complete = f"{br.organization}/{br.repository}"
    # if br.tag:
    #     complete += f":{br.tag}"
    if br.registry:
        complete = f"{br.registry}/{complete}"
    if br.digest:
        complete += f"@{br.digest}"
    return DockerCompleteImageName(complete)
