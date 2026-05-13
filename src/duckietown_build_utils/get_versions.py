import json
import os
import sys
from json import JSONDecodeError
from typing import Dict, TypedDict

from docker import DockerClient
from docker.errors import ContainerError
from zuper_commons.fs import mkdirs_thread_safe, write_ustring_to_utf8_file
from zuper_commons.types import ZException, ZValueError

from duckietown_build_utils import DockerCompleteImageName
from . import logger

__all__ = ["VersionInfo", "CannotGetVersions", "get_python_packages_versions"]


class VersionInfo(TypedDict):
    version: str
    location: str


class CannotGetVersions(ZException):
    pass


def get_python_packages_versions(
    image_name: DockerCompleteImageName, shared_tmpdir: str
) -> Dict[str, VersionInfo]:
    dn = os.path.join(shared_tmpdir, "get_python_packages_versions")

    mkdirs_thread_safe(dn)
    fn = os.path.join(dn, "eval.py")
    write_ustring_to_utf8_file(identify, fn)

    volumes = {dn: {"bind": dn, "mode": "ro"}}
    client = DockerClient.from_env()
    logger.debug(f"reading versions from {image_name}")
    try:
        res0 = client.containers.run(
            image=image_name,
            entrypoint="bash",
            command=["-c", f"python3 {fn}"],
            remove=True,
            volumes=volumes,
        )
    except ContainerError as e:
        msg = "Cannot get versions for image"
        raise CannotGetVersions(msg, image_name=image_name) from e
    res = res0.decode("utf-8")
    try:
        packages = json.loads(res)
    except JSONDecodeError:
        msg = "Cannot decode JSON"
        raise ZValueError(msg, res=res)
    return packages


# language=python
identify = """

import pip  # needed to use the pip functions
import pkg_resources
import sys
import json
import time



def _get_installed_distributions(
    local_only: bool = True,
    user_only: bool = False,
    paths=None,
):
    from pip._internal.metadata import get_environment
    from pip._internal.metadata.pkg_resources import Distribution as _Dist

    env = get_environment(paths)
    dists = env.iter_installed_distributions(
        local_only=local_only,
        user_only=user_only,
        skip=[],
    )
    return [ dist._dist for dist in dists]


packages = {}
for i in _get_installed_distributions(local_only=False):
    #print(i.__dict__)

    pkg = {
        #'project_name': i.project_name,
        'version': i._version,
        'location': i.location
    }
    packages[i.project_name] = pkg

    # assert isinstance(i, (pkg_resources.EggInfoDistribution, pkg_resources.DistInfoDistribution))

ps = sorted(packages)
packages = {k: packages[k] for k in ps}

print(json.dumps(packages, indent=2))
sys.stdout.flush()
sys.stderr.write('Finished.\\n')
sys.stderr.flush()
time.sleep(2)
"""

if __name__ == "__main__":
    a = get_python_packages_versions(DockerCompleteImageName(sys.argv[1]), "/tmp/duckietown/share")
    logger.info(res=a)
