import datetime
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import *

from duckietown_challenges import dclogger
from duckietown_challenges.utils import tag_from_date


@dataclass
class BuildResult:
    registry: Optional[str]
    organization: str
    repository: str
    tag: str
    digest: Optional[str]

    def __post_init__(self):
        if self.digest is not None:
            if not self.digest.startswith('sha256'):
                msg = 'Unknown digest format: %s ' % self.digest
                raise ValueError(msg)
            if self.digest.startswith('sha256:sha256'):
                msg = 'What happened here? %s ' % self.digest
                raise ValueError(msg)


# localhost:5000/andreacensi/aido2_simple_prediction_r1-step1-simulation-evaluation:2019_04_03_20_03_28@sha256:9c1ed66dc31ad9f1b6e454448f010277e38edf051f15b56ff985ec4292290614

def parse_complete_tag(x: str) -> BuildResult:
    ns = x.count('/')
    if ns == 2:
        registry, rest = x.split('/', maxsplit=1)

    elif ns == 1:
        registry = None
        rest = x
    else:
        msg = 'Could not parse complete tag: %s' % x
        raise ValueError(msg)

    n = rest.count(':')
    if n:
        org_repo, tag = rest.split(':', maxsplit=1)
    else:
        org_repo = rest
        tag = None

    if org_repo.count('/') != 1:  # XXX
        raise ValueError((x, rest, org_repo))

    organization, repository = org_repo.split('/')

    if tag is not None and '@' in tag:
        tag, digest = tag.split('@')
        if not digest.startswith('sha256'):
            msg = 'Unknown digest format: %s for %s' % (digest, x)
            raise ValueError(msg)
    else:
        digest = None
    try:
        return BuildResult(registry=registry, organization=organization, repository=repository,
                           tag=tag, digest=digest)
    except ValueError as e:
        raise ValueError(x) from e


def get_complete_tag(br: BuildResult):
    complete = '%s/%s' % (br.organization, br.repository)
    if br.tag is not None:
        complete += f':{br.tag}'
    if br.registry:
        complete = f'{br.registry}/{complete}'
    if br.digest is not None:
        complete += f'@{br.digest}'
    return complete


def submission_build(username: str,
                     registry: Optional[str],
                     no_cache: bool = False) -> BuildResult:
    tag = tag_from_date(datetime.datetime.now())
    df = 'Dockerfile'
    organization = username.lower()
    repository = 'aido-submissions'
    image = '%s/%s:%s' % (organization, repository, tag)

    if registry is not None:
        complete_image = f'{registry}/{image}'
    else:
        complete_image = image

    if not os.path.exists(df):
        msg = 'I expected to find the file "%s".' % df
        raise Exception(msg)

    cmd = ['docker', 'build',
           '--pull',
           '-t', complete_image,
           '-f', df,
           '.',
           ]

    if no_cache:
        cmd.append('--no-cache')
    dclogger.info('Running: %s' % " ".join(cmd))
    p = subprocess.Popen(cmd)
    p.communicate()
    if p.returncode != 0:
        msg = 'Could not run docker build.'
        raise Exception(msg)

    cmd = ['docker', 'push', complete_image]
    dclogger.info('Pushing the image: %s' % " ".join(cmd))

    p = subprocess.Popen(cmd)
    p.communicate()
    if p.returncode != 0:
        msg = 'Could not run docker push. Exit code %s.' % p.returncode
        msg += "\n\nThis is likely to be because you have not logged in to dockerhub using `docker login`."
        raise Exception(msg)

    dclogger.info('After pushing; please wait...')

    try:
        stdout = subprocess.check_output(cmd, stderr=sys.stderr)
    except subprocess.CalledProcessError as e:
        msg = 'Could not run docker push.'

        msg += '\n\nI tried to push the tag\n\n   %s' % image

        msg += '\n\nYou told me your DockerHub username is "%s"' % username

        msg += '\n\nEither the username is wrong or you need to login using "docker login".'

        msg += '\n\nTo change the username use\n\n    dts challenges config --docker-username USERNAME'
        raise Exception(msg) from e

    dclogger.info('Decoding output')
    data = stdout.decode('utf-8')
    tokens = data.split()
    digest = None
    for t in tokens:
        if t.startswith('sha256:'):
            digest = t

    if digest is None:
        msg = 'Cannot find digest in output of docker push.'
        msg += '\n\n' + data
        raise Exception(msg)

    return BuildResult(registry=registry, organization=organization, repository=repository, digest=digest,
                       tag=tag)
