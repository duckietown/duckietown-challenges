import argparse
import subprocess
import sys
import traceback
from dataclasses import dataclass
from typing import List, Optional

from zuper_commons.fs import DirPath
from zuper_commons.types import ZException, ZValueError
from . import logger

__all__ = ["aido_dir_status_main", "DirInfo", "get_dir_info", "repo_info_from_url"]


@dataclass
class DirInfo:
    tag: Optional[str]
    """ Tag for the commit """
    branch: str
    dirty: bool
    added: List[str]
    modified: List[str]
    deleted: List[str]
    untracked: List[str]
    closest_tag: Optional[str]
    repo_name: str
    sha: str
    vcs_url: str
    org_name: str


class CannotGetDirInfo(ZException):
    pass


def get_dir_info(dirname: str) -> DirInfo:
    tag = get_tag(dirname)
    context = dict(dirname=dirname)
    try:
        modified, added, deleted, untracked = get_status(dirname)
    except Exception as e:
        msg = "Cannot get file status"
        raise CannotGetDirInfo(msg, **context) from e

    try:
        sha = get_sha(dirname)
    except Exception as e:
        msg = "Cannot get commit SHA"
        raise CannotGetDirInfo(msg, **context) from e

    try:
        if tag is None:
            closest_tag = get_closest_tag(dirname)
        else:
            closest_tag = None
    except Exception as e:
        msg = "Cannot get closest tag"
        raise CannotGetDirInfo(msg, **context) from e

    try:
        repo_info = get_origin_url_repo(dirname)
    except Exception as e:
        msg = "Cannot get origin URL"
        raise CannotGetDirInfo(msg, **context) from e

    try:
        branch = get_branch(dirname)
    except Exception as e:
        msg = "Cannot get branch name"
        raise CannotGetDirInfo(msg, **context) from e

    dirty = bool(modified or added or deleted or untracked)
    if dirty:
        sha += "-dirty"
    di = DirInfo(
        tag=tag,
        dirty=dirty,
        modified=modified,
        added=added,
        deleted=deleted,
        untracked=untracked,
        vcs_url=repo_info.origin_url,
        closest_tag=closest_tag,
        repo_name=repo_info.repo,
        org_name=repo_info.org,
        sha=sha,
        branch=branch,
    )
    return di


def get_sha(dirname: str) -> str:
    sha = _run_cmd(["git", "-C", dirname, "rev-parse", "HEAD"])[0]
    return sha


def get_branch(dirname: str) -> str:
    branch = _run_cmd(["git", "-C", dirname, "rev-parse", "--abbrev-ref", "HEAD"])[0]
    return branch


def get_head_tag(dirname: str) -> Optional[str]:
    head_tag = _run_cmd(
        [
            "git",
            "-C",
            dirname,
            "describe",
            "--exact-match",
            "--tags",
            "HEAD",
        ]
    )

    head_tag = head_tag[0] if head_tag else None
    return head_tag


def get_closest_tag(dirname: str) -> Optional[str]:
    closest_tag = _run_cmd(["git", "-C", dirname, "tag"])
    closest_tag = closest_tag[-1] if closest_tag else None
    return closest_tag


@dataclass
class RepoInfo:
    origin_url: str
    org: str
    repo: str


from urllib.parse import urlparse


def interpret_http_remote(url: str) -> RepoInfo:
    comps = urlparse(url)
    # logger.info(comps=comps)
    path = comps.path.lstrip("/").rstrip(".git")
    # logger.info(comps=comps, path=path)
    if path.count("/") == 1:
        org, repo = path.split("/")
        return RepoInfo(url, org=org, repo=repo)
    else:
        msg = "Expect one / in path."
        raise ZValueError(msg, comps=comps, path=path)


def repo_info_from_url(origin_url0: str) -> RepoInfo:
    if not origin_url0:
        msg = "Cannot interpret empty url."
        raise ValueError(msg)

    # if origin_url0.startswith('git://'):
    #     origin_url0 = origin_url0.replace('')
    try:
        if any(origin_url0.startswith(_) for _ in ("git:", "http:", "https:")):
            return interpret_http_remote(origin_url0)
        elif "@" in origin_url0:
            return interpret_ssh_remote(origin_url0)
        else:
            msg = f"Looking for `http` or `@` in url {origin_url0!r}"
            raise ValueError(msg)
    except Exception as e:
        msg = f"Cannot interpret the remote url {origin_url0!r}."
        raise Exception(msg) from e


def interpret_ssh_remote(origin_url0: str) -> RepoInfo:
    origin_url = origin_url0
    if origin_url.endswith(".git"):
        origin_url = origin_url[:-4]
    if origin_url.endswith("/"):
        origin_url = origin_url[:-1]
    host, _, rest = origin_url.partition(":")
    org, repo = rest.split("/")
    # logger.info(origin_url=origin_url, org=org, repo=repo)
    return RepoInfo(org=org, repo=repo, origin_url=origin_url0)


def get_origin_url_repo(dirname: str) -> RepoInfo:
    origin_url0 = _run_cmd(["git", "-C", dirname, "config", "--get", "remote.origin.url"])[0]
    return repo_info_from_url(origin_url0)


def _run_cmd(cmd: List[str]) -> List[str]:
    # logger.debug(cmd)
    output = subprocess.check_output(cmd)

    lines = output.decode("utf-8").split("\n")

    return [line.strip() for line in lines if line.strip()]


def get_status(dirname: str):
    cmd = ["git", "status", "--porcelain"]
    res = subprocess.run(cmd, cwd=dirname, capture_output=True)
    if res.returncode:
        msg = "Cannot run git status"
        raise ZException(msg, res=res)

    stdout = res.stdout.decode()
    lines = stdout.split("\n")

    modified = []
    added = []
    untracked = []
    deleted = []

    IGNORE = []
    for l in lines:
        l = l.strip()
        if not l:
            continue
        status, _, filename = l.partition(" ")

        if filename in IGNORE:
            continue

        # logger.info(status=status, filename=filename)

        status0 = status[0]
        if status0 == "?":
            untracked.append(filename)
        elif status0 in ["M"]:
            modified.append(filename)
        elif status0 in ["U"]:
            modified.append(filename)
        elif status0 in ["A"]:
            added.append(filename)
        elif status0 in ["D"]:
            deleted.append(filename)
        elif status0 in ["R", "C"]:
            modified.append(filename)
        else:
            logger.warning("Cannot interpret line", l=l)
            # raise ZException(stdout=stdout)
    return modified, added, deleted, untracked


def get_tag(dirname: DirPath) -> Optional[str]:
    cmd = ["git", "describe", "--exact-match", "--tags"]
    res = subprocess.run(cmd, cwd=dirname, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tagged = res.returncode == 0
    if tagged:
        tag = res.stdout.decode().strip()
    else:
        tag = None
    return tag


def aido_dir_status_main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", "-d", default=".")
    parsed = parser.parse_args(args)
    dirname = parsed.directory
    # noinspection PyBroadException
    try:
        res = get_dir_info(dirname)
        logger.info(res=res)
    except SystemExit:
        raise
    except BaseException:
        logger.error(traceback.format_exc())
        sys.exit(3)
