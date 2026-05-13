from typing import cast, Dict, Iterator, List, Optional

from zuper_commons.types import ZValueError
from . import logger
from .buildresult import parse_complete_tag
from .misc import get_important_env_build_args_dict
from .types import DockerCompleteImageName

__all__ = ["get_resolved_from"]


def get_lines(dockerfile_contents: str) -> Iterator[str]:
    dockerfile_contents = dockerfile_contents.replace("\\\n", " ")
    lines = dockerfile_contents.split("\n")
    for line in lines:
        line = line.strip()
        if "#" in line:
            i = line.find("#")
            line = line[:i]
        line = line.strip()
        if line:
            yield line


def get_FROM(dockerfile_contents: str) -> List[str]:
    res = []
    lines = list(get_lines(dockerfile_contents))
    for line in lines:

        if line.startswith("FROM"):
            x = line.replace("FROM", "")

            x = x.strip()
            xs = x.split(" ")
            if xs:
                res.append(xs[0])
    if not res:
        msg = "Expecting at least 1 FROM."
        raise ZValueError(msg, lines=lines)
    return res


def get_args(dockerfile_contents: str) -> Dict[str, Optional[str]]:
    res = {}
    lines = list(get_lines(dockerfile_contents))
    for line in lines:

        if line.startswith("ARG"):
            x = line.replace("ARG", "")
            x = x.strip()
            if "=" in x:
                k, _, v = x.partition("=")
                k = k.strip()
                v = v.strip()
            else:
                k = x
                v = None

            if k not in res or v is not None:
                res[k] = v

    return res


def replace_vars(s: str, variables: Dict[str, str]) -> str:
    for vname, v in variables.items():
        vref = "${%s}" % vname
        if vref in s:
            if v is None:
                msg = f"Cannot replace variable {vname!r} because value is None."
                raise ZValueError(msg, s=s, variables=variables)
            s = s.replace(vref, v)
    return s


def get_resolved_from(dockerfile_contents: str) -> List[DockerCompleteImageName]:
    varvalues = get_important_env_build_args_dict(dockerfile_contents)

    res = []
    lines = list(get_lines(dockerfile_contents))
    variables = get_args(dockerfile_contents)
    variables0 = dict(variables)

    for k, v in list(variables.items()):
        # if k in os.environ:
        #     v2 = os.environ[k]
        # else:
        if k in varvalues:
            v2 = varvalues[k]
        else:
            v2 = v
            # else:
            #     msg = 'Variable does not have default'
            #     raise ZValueError(msg, k=k, v=v, variables=variables,
            #     dockerfile_contents=dockerfile_contents)
        variables[k] = v2

    # variables["ARCH"] = arch  # XXX
    # logger.debug(varvalues=varvalues, variables0=variables0, variables=variables)
    froms = get_FROM(dockerfile_contents)
    # logger.debug(froms=froms)
    for f in froms:
        i = f

        # do it to take care of recusrive defs
        try:
            for _ in range(4):
                i = replace_vars(i, variables)
        except ValueError as e:
            msg = f"Cannot replace variables in {f!r}"
            raise ZValueError(msg, lines=lines) from e

        # do it 3
        if "$" in i:
            msg = "Cannot replace all variables"
            raise ZValueError(msg, froms=froms, variables=variables, lines=lines)
        i = cast(DockerCompleteImageName, i)
        br = parse_complete_tag(i)
        res.append(i)

    logger.info(resolved=res)
    return res
