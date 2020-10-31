from dataclasses import dataclass
from typing import Optional

__all__ = ["BuildResult", "parse_complete_tag", "get_complete_tag", "submission_read"]


@dataclass
class BuildResult:
    registry: Optional[str]
    organization: str
    repository: str
    tag: str
    digest: Optional[str]

    def __post_init__(self):
        if self.repository:
            assert not "@" in self.repository, self
        if self.tag:
            assert not "@" in self.tag, self

        if self.digest is not None:
            if not self.digest.startswith("sha256"):
                msg = f"Unknown digest format: {self.digest} "
                raise ValueError(msg)
            if self.digest.startswith("sha256:sha256"):
                msg = f"What happened here? {self.digest} "
                raise ValueError(msg)


# localhost:5000/andreacensi/aido2_simple_prediction_r1-step1-simulation-evaluation:2019_04_03_20_03_28@sha256
# :9c1ed66dc31ad9f1b6e454448f010277e38edf051f15b56ff985ec4292290614


def parse_complete_tag(x: str) -> BuildResult:
    ns = x.count("/")
    if ns == 2:
        registry, rest = x.split("/", maxsplit=1)

    elif ns == 1:
        registry = "docker.io"
        rest = x
    else:
        msg = "Could not parse complete tag: %s" % x
        raise ValueError(msg)

    nsha = rest.count("@")
    if nsha:
        rest, digest = rest.split("@")
        if not digest.startswith("sha256"):
            msg = f"Unknown digest format: {digest} for {x}"
            raise ValueError(msg)
    else:
        digest = None

    n = rest.count(":")
    if n:
        org_repo, tag = rest.split(":", maxsplit=1)
    else:
        org_repo = rest
        tag = None

    if org_repo.count("/") != 1:  # XXX
        raise ValueError((x, rest, org_repo))

    organization, repository = org_repo.split("/")

    try:
        return BuildResult(
            registry=registry, organization=organization, repository=repository, tag=tag, digest=digest,
        )
    except ValueError as e:
        raise ValueError(x) from e


def get_complete_tag(br: BuildResult):
    complete = f"{br.organization}/{br.repository}"
    if br.tag:
        complete += f":{br.tag}"
    if br.registry:
        complete = f"{br.registry}/{complete}"
    if br.digest:
        complete += f"@{br.digest}"
    return complete
