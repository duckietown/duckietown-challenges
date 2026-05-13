import sys
from typing import cast, List, Optional

import requirements
from packaging import version

# # noinspection PyCompatibility,PyProtectedMember
# from pip._internal.utils.misc import get_installed_distributions
#
# # noinspection PyCompatibility,PyProtectedMember
# from pip._vendor.pkg_resources import DistInfoDistribution, Distribution, EggInfoDistribution


def _get_installed_distributions(
    local_only: bool = True,
    user_only: bool = False,
    paths: Optional[List[str]] = None,
):
    """Return a list of installed Distribution objects."""
    from pip._internal.metadata import get_environment
    from pip._internal.metadata.pkg_resources import Distribution as _Dist

    env = get_environment(paths)
    dists = env.iter_installed_distributions(
        local_only=local_only,
        user_only=user_only,
        skip=[],
    )
    return [cast(_Dist, dist)._dist for dist in dists]


from . import logger

__all__ = ["update_reqs_versions_main"]


def include(req):
    name = req.name
    if "aido" in name:
        return True
    if "zuper" in name:
        return True
    if "dt-" in name:
        return True
    if "duckietown" in name:
        return True
    return False


def update_reqs_versions_main(args=None):
    packages = {}

    for i in _get_installed_distributions(local_only=True):
        # print(type(i))
        # print(i)
        # print(i.__dict__)
        # assert isinstance(i, (pip._vendor.pkg_resources.DistInfoDistribution, ))
        # assert isinstance(i, (EggInfoDistribution, DistInfoDistribution, Distribution)), type(i)
        packages[i.project_name] = i.version
        # pkg = {
        #     # 'project_name': i.project_name,
        #     'version': i._version,
        #     'location': i.location
        # }
        # # packages[i.project_name] = pkg

    the_args = args or sys.argv
    filename = the_args[1]

    with open(filename, "r") as fd:
        for req in requirements.parse(fd):
            if not include(req):
                continue
            # print(req.name, req.specs)

            if req.name in packages:
                v = packages[req.name]
                for (what, version) in req.specs:
                    if what == "==":
                        if is_lower_than(version, packages[req.name]):
                            msg = f"Warning: reqs says {req.name}=={version} but I know {v}."
                            logger.error(msg)
                            sys.exit(1)

    # print(json.dumps(packages, indent=2))


def is_lower_than(version1: str, version2: str) -> bool:
    return version.parse(version1) < version.parse(version2)
