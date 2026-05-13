import getpass
import os
import sys
import time
import traceback
from dataclasses import replace
from typing import Optional

import yaml
from docker import DockerClient
from zuper_commons.fs import write_ustring_to_utf8_file
from zuper_commons.types import ZException, ZValueError

from . import logger
from .buildresult import get_complete_tag, parse_complete_tag
from .caching import docker_caching
from .credentials import DockerCredentials
from .docker_logging_in import do_login_for_registry
from .types import DockerCompleteImageName, DockerImageDigest

__all__ = ["docker_push_optimized", "docker_push_retry", "DockerPushFailure", "docker_push_optimized_"]


def docker_push_retry(
    client: DockerClient,
    image_name: DockerCompleteImageName,
    credentials: DockerCredentials,
) -> DockerImageDigest:
    while True:
        # noinspection PyBroadException
        try:
            # logger.info(f"Pushing {image_name}")
            return push_image(client, image_name, progress=True, credentials=credentials)
        except ZValueError:
            raise
        except:
            logger.error(traceback.format_exc())
            logger.error("retrying in 5 seconds")
            time.sleep(5)


class DockerPushFailure(ZException):
    pass


def docker_push_optimized(
    client: DockerClient,
    image_name: DockerCompleteImageName,
    credentials: DockerCredentials,
) -> DockerCompleteImageName:
    """Returns the *complete tag* for the image  "a/b:@sha256:...". Without tags."""
    f = parse_complete_tag(image_name)

    return docker_push_optimized_(client, image_name, credentials)


def docker_push_optimized_(
    client,
    image_name: DockerCompleteImageName,
    credentials: DockerCredentials,
) -> DockerCompleteImageName:
    """Returns the *complete tag* for the image  "a/b:@sha256:...". Without tags."""
    f = parse_complete_tag(image_name)

    image = client.images.get(image_name)
    image_name_no_tag, _, _ = image_name.partition(":")
    # XXX: apparently docker does not store 'docker.io'
    image_name_no_tag = image_name_no_tag.replace("docker.io/", "")
    # RepoTags = image.attrs["RepoTags"]
    # RepoTags = [_ for _ in RepoTags if _.startswith(image_name_no_tag)]
    RepoDigests = image.attrs["RepoDigests"]
    RepoDigests = [_ for _ in RepoDigests if _.startswith(image_name_no_tag)]
    # logger.debug(f"RepoTags {RepoTags}")
    # logger.debug(f"RepoDigests {RepoDigests}")

    if RepoDigests and ("DT_PUSH_OPT" in os.environ):
        logger.debug(f"RepoDigests already present; skipping pushing: {RepoDigests}")
        return RepoDigests[0]
    digest_from_push = docker_push_retry(client, image_name, credentials=credentials)

    f = replace(f, tag=None, digest=digest_from_push)
    return get_complete_tag(f)


def push_image(
    client: DockerClient, image_name: DockerCompleteImageName, progress: bool, credentials: DockerCredentials
) -> DockerImageDigest:
    br = parse_complete_tag(image_name)

    if br.tag is None and br.digest is None:
        msg = "Expecting either tag or digest"
        raise ZValueError(msg, image_name=image_name, br=br)

    im = client.images.get(image_name)
    image_id = im.id
    if br.tag is not None:

        try:
            when, digest = docker_caching.get_last_tag_push(
                br.registry, br.organization, br.repository, br.tag, image_id
            )
        except KeyError:
            pass

        else:
            msg = "Tag already pushed"
            logger.info(msg, image_id=image_id, br=br, when=when, digest=digest)
            return digest
    else:
        try:
            when, digest = docker_caching.get_last_image_push(
                br.registry, br.organization, br.repository, image_id
            )
        except KeyError:
            pass

        else:
            msg = "Image already pushed"
            logger.info(msg, image_id=image_id, br=br, when=when, digest=digest)
            return digest

    layers = set()
    pushed = set()
    logger.info(f"Pushing image", image_name=image_name, image_id=image_id)
    tag = parse_complete_tag(image_name)
    image_name_short = f"{tag.repository}"

    do_login_for_registry(client, credentials, tag.registry)

    layer2size = {}
    layer2done = {}

    update_interval = 2
    last_update = 0.0
    # last_ps = ''
    last_progress = ""
    nlines = 0
    spinner = list("◐◓◑◒")
    all_lines = []
    final_digest: Optional[DockerImageDigest] = None

    for line in client.images.push(image_name, stream=True, decode=True):
        all_lines.append(line)
        nlines += 1
        # logger.info(line=line)
        # percentage = max(0.0, min(1.0, len(pushed) / max(1.0, len(layers)))) * 100.0
        if "error" in line:
            msg = "Cannot push image"
            l = str(line["error"])
            raise DockerPushFailure(msg, image_name=image_name, error=l)

        if "aux" in line:
            if "Digest" in line["aux"]:
                final_digest = DockerImageDigest(line["aux"]["Digest"])

        # aux:
        # Tag: daffy - amd64
        # Digest: sha256:a4c1b0756713ad2201d1b5588ea527ebd69e01cddf8df1d81a36885d4dad67cc
        # Size: 5984
        if "progress" in line:
            last_progress = line["progress"]
        if "id" in line:
            layer_id = line["id"]
            layers.add(layer_id)
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
                    layer2size[layer_id] = total
                    layer2done[layer_id] = current
            if "status" in line:
                if line["status"] in ["Layer already exists", "Pushed"]:
                    pushed.add(layer_id)

        if layers:
            fraction_layers_done = float(len(pushed)) / len(layers)
        else:
            fraction_layers_done = 0.0
        # total_bytes = sum(layer2size.values())
        # bytes_done = sum(layer2done.values())
        # if total_bytes:
        #     fraction_bytes_done = float(bytes_done) / total_bytes
        # else:
        #     fraction_bytes_done = 0.0

        now = time.time()

        # def fancy(x):
        #     y = x / (1000 * 1000.0)
        #     return f"{int(y)} MB"

        lprogress = f"{fraction_layers_done * 100:4.1f}% ({len(pushed):3}/{len(layers):3})"
        # bprogress = f"{fraction_bytes_done * 100:4.1f}% ({fancy(bytes_done)}/{fancy(total_bytes)})"

        spinneri = spinner[nlines % len(spinner)]
        ps = f"%[pushing {image_name_short}] {lprogress} {spinneri} {last_progress}"

        if progress:
            if now - last_update >= update_interval:  # or last_ps != ps:
                last_update = now
                # last_ps = ps

                sys.stderr.write(ps + "\n")
                sys.stderr.flush()

    logger.debug(f"Push successful.", image_name=image_name, final_digest=final_digest)

    user = getpass.getuser()
    try:
        fn = f"/tmp/{user}/duckietown/dt-build-utils/" + tag.repository + ".push_history.yaml"
        write_ustring_to_utf8_file(yaml.dump(all_lines), fn)
    except:
        pass

    if br.tag is not None:
        docker_caching.mark_tag_pushed(
            br.registry, br.organization, br.repository, br.tag, image_id, final_digest
        )
    docker_caching.mark_image_pushed(br.registry, br.organization, br.repository, image_id, final_digest)

    return final_digest
