import os

import requirements
from duckietown_build_utils import get_last_version_fresh
from requirements.requirement import Requirement

from zuper_commons.fs import write_ustring_to_utf8_file
from zuper_commons.types import ZException, ZValueError
from . import logger

__all__ = ["update_versions"]


def update_versions(fn="requirements.txt", out="requirements.resolved"):
    if not os.path.exists(fn):
        logger.debug("Requirement file does not exist", fn=fn)

        if os.path.exists(out):
            msg = "Found a resolved requirements file but not its .txt "
            logger.error(msg, found=out, notfound=fn)
            raise ZException(msg, found=out, notfound=fn)

        return

    logger.info(f"Now updating requirements files", fn=fn, out=out)
    # logger.info("Parsing reqs", fn=fn)
    data2 = []
    with open(fn) as fd:
        req: Requirement
        for req in requirements.parse(fd):
            todo = (len(req.specs) == 0) or (len(req.specs) == 1 and req.specs[0][0] in (">=", ">"))
            if todo:
                v = get_last_version_fresh(req.name)
                if v is None:
                    msg = f"Cannot find the package {req.name}"
                    raise ZValueError(msg)

                logger.debug(f"Updated package   {req.name} to {v}")
                req.specs = [("==", v)]
            else:
                logger.debug(f"skipping spec {req}", specs=req.specs)

            ss = ",".join(f"{a}{b}" for a, b in req.specs)
            s2 = f"{req.name}{ss}"
            data2.append(s2)
            # logger.info(req=req, rd=req.__dict__, v=v)

    # add space because it will be easier to cat files together
    res = "\n" + "\n".join(data2) + "\n\n"
    # logger.info(res=res)
    write_ustring_to_utf8_file(res, out)
