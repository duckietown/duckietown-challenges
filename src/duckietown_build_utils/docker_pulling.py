import sys
import time
import traceback
from dataclasses import dataclass, replace
from typing import Dict, Iterator, Optional, Set

from docker import DockerClient
from zuper_commons.types import ZException, ZValueError

from . import logger
from .buildresult import (
    BuildResult,
    get_complete_tag,
    get_complete_tag_notag,
    parse_complete_tag,
)
from .caching import docker_caching
from .credentials import DockerCredentials
from .docker_logging_in import do_login_for_registry
from .dockerfile_utils import get_resolved_from
from .types import DockerCompleteImageName, DockerImageDigest

__all__ = ["PullError", "docker_pull", "docker_pull_retry", "pull_for_build"]


class PullError(ZException):
    pass


@dataclass
class DockerPullResult:
    br: BuildResult
    complete_image_name: DockerCompleteImageName


def docker_pull_retry(
    client: DockerClient,
    image_name: DockerCompleteImageName,
    ntimes: int,
    wait: float,
    quiet: bool,
    credentials: DockerCredentials,
) -> DockerPullResult:
    for i in range(ntimes + 1):
        try:
            # logger.info(f"Pushing {image_name}")
            return docker_pull(client, image_name, quiet=quiet, credentials=credentials)
        except PullError as e:
            if i == ntimes:
                msg = f"After trying {ntimes} I still could not pull {image_name}"
                raise PullError(msg) from e

            s = traceback.format_exc()
            logger.warning(s)
            logger.info(f"I will retry in {wait} seconds")
            time.sleep(wait)


def docker_pull(
    client: DockerClient, image: DockerCompleteImageName, quiet: bool, credentials: DockerCredentials
) -> DockerPullResult:
    image0 = image
    br = parse_complete_tag(image)
    image = get_complete_tag(br)
    if image0 != image:
        logger.debug(f"Pulling {image0} -> {image}")
    else:
        logger.debug(f"Pulling {image}")

    if br.digest is None and br.tag is not None:
        try:
            when, image_id, digest = docker_caching.get_last_tag_push_any(
                br.registry, br.organization, br.repository, br.tag
            )

        except KeyError:
            pass
        else:
            logger.info(f"using cached pull info for {image}")

            br2 = replace(br, digest=digest, tag=None)
            return DockerPullResult(br2, get_complete_tag(br2))

    do_login_for_registry(client, credentials, br.registry)

    repository = get_complete_tag_notag(br)
    short_repo = br.repository

    last_update = 0.0
    update_interval = 0
    ps: Optional[PullStatus] = None
    try:
        pulling = client.api.pull(repository=repository, tag=br.tag, stream=True, decode=True)

        for ps in yield_updates(pulling):

            now = time.time()
            lprogress = f"{ps.fraction_layers_done * 100:4.1f}% ({len(ps.pulled):3}/{len(ps.layers):3})"
            # bprogress = f"{ps.fraction_bytes_done * 100:4.1f}% ({fancy(ps.bytes_done)}/{fancy(
            # ps.total_bytes)})"
            # ps = f"pulling {repository} layers: {lprogress} bytes {bprogress}"
            pst = f"%[pulling {short_repo}] {lprogress} {ps.last_progress}"

            if now - last_update >= update_interval:  # or last_ps != ps:
                last_update = now

                if not quiet:
                    sys.stderr.write(pst + "\n")
                    sys.stderr.flush()
    except APIError as e:
        msg = f"Cannot pull repo  {repository}  tag  {br.tag}"
        raise PullError(msg) from e

    logger.debug(f"Pulled {image} -> {ps.final_digest}")

    if not ps.final_digest:
        raise PullError(f"could not find final digest for {image} - perhaps docker failed. Please re-try.")

    br = parse_complete_tag(image)
    br2 = replace(br, digest=ps.final_digest, tag=None)
    image = client.images.get(get_complete_tag(br2))
    if br.tag is not None:
        docker_caching.mark_tag_pushed(
            br.registry, br.organization, br.repository, br.tag, image.id, ps.final_digest
        )
    return DockerPullResult(br2, get_complete_tag(br2))


from docker.errors import APIError


@dataclass
class PullStatus:
    layers: Set[str]
    pulled: Set[str]
    layer2size: Dict[str, int]
    layer2done: Dict[str, int]
    fraction_bytes_done: float
    fraction_layers_done: float
    total_bytes: int
    bytes_done: int
    last_progress: str
    final_digest: Optional[DockerImageDigest]


def yield_updates(updates: Iterator[dict]) -> Iterator[PullStatus]:
    PS = PullStatus(set(), set(), {}, {}, 0.0, 0.0, 0, 0, "", None)
    yield PS
    # last_ps = ''
    last_progress = ""
    all_lines = []
    for line in updates:
        all_lines.append(line)
        # logger.info(line=line)
        # percentage = max(0.0, min(1.0, len(pushed) / max(1.0, len(layers)))) * 100.0
        if "progress" in line:
            last_progress = line["progress"]

        if "status" in line:
            status = line["status"]
            P = "Digest: "
            if status.startswith(P):
                final_digest = status.replace(P, "")
                if not final_digest.startswith("sha256:"):
                    raise ZValueError("Invalid digest", line=line)
                PS.final_digest = final_digest
        if "id" in line:
            layer_id = line["id"]
            PS.layers.add(layer_id)
            if "progressDetail" in line:
                progd = line["progressDetail"]
                if progd:
                    if "current" in progd:
                        current = progd["current"]
                    else:
                        current = 0
                    if "total" in progd:
                        total = progd["total"]
                    else:
                        total = 1
                    # total = line['progressDetail']['total']
                    PS.layer2size[layer_id] = total
                    PS.layer2done[layer_id] = current
            if "status" in line:
                if line["status"] in ["Pull complete", "Already exists"]:
                    PS.pulled.add(layer_id)

        if PS.layers:
            PS.fraction_layers_done = float(len(PS.pulled)) / len(PS.layers)
        else:
            PS.fraction_layers_done = 0.0
        PS.total_bytes = sum(PS.layer2size.values())
        PS.bytes_done = sum(PS.layer2done.values())
        PS.last_progress = last_progress
        if PS.total_bytes:
            PS.fraction_bytes_done = float(PS.bytes_done) / PS.total_bytes
        else:
            PS.fraction_bytes_done = 0.0

        yield PS
    PS.fraction_layers_done = 1.0
    PS.fraction_bytes_done = 1.0
    PS.last_progress = f"Done: {PS.final_digest}"
    yield PS
    if PS.final_digest is None:
        msg = "Weird problem - I could not get the result of the pull"
        raise ZValueError(msg, all_lines=all_lines)
        #
        # now = time.time()
        #
        # def fancy(x):
        #     y = x / (1000 * 1000.0)
        #     return f'{int(y)} MB'
        #
        # lprogress = f'{fraction_layers_done * 100:4.1f}% ({len(pushed):3}/{len(layers):3})'
        # bprogress = f'{fraction_bytes_done * 100:4.1f}% ({fancy(bytes_done)}/{fancy(total_bytes)})'
        # ps = f'pushing {image_name_short} layers: {lprogress} bytes {bprogress}'
        #
        # if now - last_update >= update_interval:  # or last_ps != ps:
        #     last_update = now
        #     last_ps = ps
        #
        #     sys.stderr.write(ps + '\n')
        #     sys.stderr.flush()


def pull_for_build(
    client: DockerClient, dockerfile_contents: str, credentials: DockerCredentials, quiet: bool
):
    for x in get_resolved_from(dockerfile_contents):
        docker_pull_retry(
            client=client, credentials=credentials, image_name=x, ntimes=3, wait=15, quiet=quiet
        )
