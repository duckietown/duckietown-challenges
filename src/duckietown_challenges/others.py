import datetime
import os
import subprocess
from dataclasses import replace
from typing import List, Optional

import yaml
from docker import DockerClient
from zuper_ipce import IESO, ipce_from_object

from dt_shell.env_checks import get_dockerhub_username
from . import logger
from .challenge import ChallengeDescription, ChallengesConstants
from .cmd_submit_build import (
    BuildResult,
    get_complete_tag,
    parse_complete_tag,
)
from .rest_methods import (
    dtserver_challenge_define,
    get_registry_info,
    RegistryInfo,
)
from .utils import tag_from_date

__all__ = ['dts_define']


def fix_none(br: BuildResult) -> BuildResult:
    if br.registry is None:
        return replace(br, registry='docker.io')
    else:
        return br


def compatible_br(rd: List[str], registry) -> List[BuildResult]:
    # logger.info(rd)
    brs = [parse_complete_tag(_) for _ in rd]
    brs = list(map(fix_none, brs))
    compatible = [_ for _ in brs if _.registry == registry]
    return compatible


def get_compatible_br(client, complete, registry) -> BuildResult:
    image = client.images.get(complete)

    repo_tags = list(reversed(sorted(image.attrs.get("RepoTags", []))))
    repo_digests = list(reversed(sorted(image.attrs.get("RepoDigests", []))))
    logger.info(f'repo_tags: {repo_tags}')
    logger.info(f'repo_digests: {repo_digests}')
    compatible_digests = compatible_br(repo_digests, registry)
    compatible_tags = compatible_br(repo_tags, registry)

    if compatible_digests and compatible_tags:
        logger.info(f'compatible: {compatible_digests} {compatible_tags}')
        br = compatible_tags[0]
        br.digest = compatible_digests[0].digest
        logger.info(f'choosing: {br}\n{get_complete_tag(br)}')
        return br
    else:
        raise KeyError()


def dts_define(token: str, impersonate: Optional[int], parsed, challenge, base,
               client: DockerClient,
               no_cache: bool):
    ri = get_registry_info(token=token, impersonate=impersonate)
    logger.info(f'impersonate {impersonate}')
    if parsed.steps:
        use_steps = parsed.steps.split(",")
    else:
        use_steps = list(challenge.steps)
    for step_name in use_steps:
        if step_name not in challenge.steps:
            msg = 'Could not find step "%s" in %s.' % (step_name, list(challenge.steps))
            raise Exception(msg)
        step = challenge.steps[step_name]

        services = step.evaluation_parameters.services
        for service_name, service in services.items():
            if service.build:
                dockerfile = service.build.dockerfile
                context = os.path.join(base, service.build.context)
                if not os.path.exists(context):
                    msg = "Context does not exist %s" % context
                    raise Exception(msg)

                dockerfile_abs = os.path.join(context, dockerfile)
                if not os.path.exists(dockerfile_abs):
                    msg = "Cannot find Dockerfile %s" % dockerfile_abs
                    raise Exception(msg)

                logger.info("context: %s" % context)
                args = service.build.args
                if args:
                    logger.warning("arguments not supported yet: %s" % args)

                username = get_dockerhub_username()

                br = build_image(
                    client,
                    context,
                    challenge.name,
                    step_name,
                    service_name,
                    dockerfile_abs,
                    no_cache,
                    registry_info=ri,
                    dopull=parsed.pull,
                    username=username
                )
                complete = get_complete_tag(br)
                service.image = complete

                # very important: get rid of it!
                service.build = None
            else:
                if service.image == ChallengesConstants.SUBMISSION_CONTAINER_TAG:
                    pass
                else:
                    vname = 'AIDO_REGISTRY'
                    vref = '${%s}' % vname
                    if vref in service.image:
                        value = os.environ.get(vname)
                        service.image = service.image.replace(vref, value)
                    logger.info(f'service = {service}')
                    br = parse_complete_tag(service.image)
                    if br.digest is None:
                        msg = "Finding digest for image %s" % service.image
                        logger.warning(msg)

                        # noinspection PyTypeChecker
                        br_no_registry = replace(br, tag=None)
                        image_name = get_complete_tag(br_no_registry)
                        image = client.images.pull(image_name, tag=br.tag)

                        # service.image_digest = image.id
                        br.digest = image.id

                        service.image = get_complete_tag(br)
                        logger.warning("complete: %s" % service.image)

    ieso = IESO(with_schema=False)
    assert challenge.date_close.tzinfo is not None, (challenge.date_close, challenge.date_open)
    assert challenge.date_open.tzinfo is not None, (challenge.date_close, challenge.date_open)
    ipce = ipce_from_object(challenge, ChallengeDescription, ieso=ieso)
    data2 = yaml.dump(ipce)
    res = dtserver_challenge_define(
        token, data2, parsed.force_invalidate_subs, impersonate=impersonate
    )
    challenge_id = res["challenge_id"]
    steps_updated = res["steps_updated"]

    if steps_updated:
        logger.info("Updated challenge %s" % challenge_id)
        logger.info("The following steps were updated and will be invalidated.",
                    steps_updated=steps_updated)
        # for step_name, reason in steps_updated.items():
        #     logger.info("\n\n" + indent(reason, " ", step_name + "   "))
    else:
        msg = "No update needed - the container digests did not change."
        logger.info(msg)


def build_image(
    client,
    path,
    challenge_name,
    step_name,
    service_name,
    filename,
    no_cache: bool,
    registry_info: RegistryInfo,
    dopull: bool,
    username: str,  # dockerhub username
) -> BuildResult:
    d = datetime.datetime.now()
    # read the content to see if we need the AIDO_REGISTRY arg?
    with open(filename) as _:
        dockerfile = _.read()

    if username.lower() != username:
        msg = f'Are you sure that the DockerHub username is not lowercase? You gave "{username}".'
        logger.warning(msg)
        username = username.lower()

    br = BuildResult(
        repository=("%s-%s-%s" % (challenge_name, step_name, service_name)).lower(),
        organization=username,
        registry=registry_info.registry,
        tag=tag_from_date(d),
        digest=None,
    )
    complete = get_complete_tag(br)

    cmd = ["docker", "build"]
    if dopull:
        cmd.append("--pull")

    cmd.extend(["-t", complete, "-f", filename])

    env_vars = ['AIDO_REGISTRY', 'PIP_INDEX_URL']
    for v in env_vars:
        if v not in dockerfile:
            continue
        val = os.getenv(v)
        if val is not None:
            cmd.append('--build-arg')
            cmd.append(f'{v}={val}')

    if no_cache:
        cmd.append("--no-cache")

    cmd.append(path)
    logger.debug("$ %s" % " ".join(cmd))
    subprocess.check_call(cmd)

    use_repo_digests = False

    if use_repo_digests:
        try:
            br = get_compatible_br(client, complete, registry_info.registry)
            return br
        except KeyError:
            pass

    logger.info("Image not present on registry. Need to push.")

    cmd = ["docker", "push", complete]
    logger.debug("$ %s" % " ".join(cmd))
    subprocess.check_call(cmd)

    image = client.images.get(complete)
    logger.info("image id: %s" % image.id)
    logger.info("complete: %s" % get_complete_tag(br))

    try:
        br0 = get_compatible_br(client, complete, registry_info.registry)
    except KeyError:
        msg = "Could not find any repo digests (push not succeeded?)"
        raise Exception(msg)

    br = parse_complete_tag(complete)
    br.digest = br0.digest

    logger.info(f'using: {br}')
    return br
