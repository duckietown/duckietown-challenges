import argparse
import json
import os
import subprocess
import sys
import traceback
from json import JSONDecodeError
from typing import Dict, Optional

import requests
from requests import Response
from zuper_commons.types import ZException, ZKeyError

from . import logger
from .commons import get_dir_info

__all__ = ["aido_check_need_upload_main", "get_last_version_fresh"]


# noinspection PyUnresolvedReferences
def download_json(url: str, headers: Dict[str, str] = None):
    headers = headers or {}

    try:

        r: Response = requests.get(url, headers=headers, timeout=20)
    except requests.exceptions.ConnectionError:

        # s = read_ustring_from_utf8_file('/etc/resolv.conf')
        # logger.error(s=s)
        raise

    # logger.info(url=url)

    if r.status_code != 200:
        logger.warning(f"code {r.status_code} for {url}", r=r.__getstate__())
        raise ZKeyError(url=url, r=r.__getstate__())
    else:

        try:
            j = json.dumps(r.json())
        except JSONDecodeError as e:
            msg = "Cannot decode JSON"
            raise ZKeyError(msg, url=url, r=r.__getstate__()) from e
        return j


def interpret_pypi(json_string):
    rj = json.loads(json_string)
    pypi_version = rj["info"]["version"]
    return pypi_version


def interpret_devpi(json_string):
    rj = json.loads(json_string)

    # logger.info(rj=rj )
    versions = list(rj["result"])

    def try_int(x):
        try:
            return int(x)
        except ValueError:
            return 0

    version_sorted = sorted(versions, key=lambda _: tuple(map(try_int, _.split("."))))

    v = version_sorted[-1]

    # logger.info(v=v, version_sorted=version_sorted)

    return v


def get_pip_server():
    default = "https://pypi.org/pypi"
    r = os.environ.get("PIP_INDEX_URL", default)
    if r.endswith("/"):
        r = r[:-1]
    return r


class CouldNotGetVersion(ZException):
    pass


def get_last_version_fresh(package_name: str) -> Optional[str]:
    pip_server = get_pip_server()
    # logger.info(pip_server=pip_server)
    if "pypi.org" in pip_server:
        pip_server = "https://pypi.org/pypi"
        url = f"{pip_server}/{package_name}/json"
        headers = {"Accept": "application/json"}
        try:
            j = download_json(url, headers=headers)
        except ZKeyError:
            return None
        return interpret_pypi(j)
    else:
        headers = {"Accept": "application/json"}
        url = f"{pip_server}/{package_name}"
        try:
            j = download_json(url, headers=headers)
        except ZKeyError:
            return None

        return interpret_devpi(j)


def aido_check_need_upload_main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", "-d", default=".")
    parser.add_argument("--package", required=True)
    parser.add_argument("cmd", nargs="*")
    parsed = parser.parse_args(args)
    # if parsed.package is None:
    #     raise ZValueError("--package")
    package = parsed.package

    # noinspection PyBroadException
    try:
        directory = parsed.directory
        absdir = os.path.realpath(directory)
        rest = parsed.cmd

        if not os.path.exists(directory):
            sys.exit(-2)

        di = get_dir_info(directory)

        if di.tag is None:
            logger.error("This is not tagged. ", directory=absdir, di=di, rest=" ".join(rest))
            sys.exit(1)

        else:
            # noinspection PyBroadException
            try:
                last_version = get_last_version_fresh(package)
            except BaseException:
                logger.error(traceback.format_exc())
                last_version = "n/a"
            # logger.info('This is tagged. ',
            #             directory=absdir, di=di, last_version=last_version)

            tag1 = f"v{last_version}"
            if tag1 == di.tag:
                logger.info(f"Already present version {last_version}", absdir=absdir, package=package)
                sys.exit(0)
            else:
                logger.info(
                    f"Tag {di.tag!r} but version {last_version!r} tag1 = {tag1!r}",
                    absdir=absdir,
                    package=package,
                )
                res = subprocess.run(rest, cwd=directory)
                sys.exit(res.returncode)

    except SystemExit:
        raise
    except BaseException:
        logger.error(traceback.format_exc())
        sys.exit(3)
