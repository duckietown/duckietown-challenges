import json
import os
import re
import subprocess
from functools import lru_cache
from tempfile import TemporaryDirectory
from typing import cast, Dict, List

from zuper_commons.fs import read_ustring_from_utf8_file, write_ustring_to_utf8_file
from . import logger
from .types import DockerCompleteImageName

__all__ = [
    "run_build_buildx",
    "add_digest_to_tag",
    "add_digest_to_tag_cached",
]


def run_build_buildx(
    path: str,
    tag: DockerCompleteImageName,
    buildargs: Dict[str, str],
    labels: Dict[str, str],
    nocache: bool,
    pull: bool,
    platforms: List[str],
    dockerfile: str,
) -> DockerCompleteImageName:
    build_args_cl = [f"--build-arg={k}={v}" for k, v in buildargs.items()]
    labels_cl = [f"--label={k}={v}" for k, v in labels.items()]
    # create a tmp dir
    with TemporaryDirectory() as tmpdir:
        metadata_file = os.path.join(tmpdir, "metadata.json")
        new_dockerfile = os.path.join(tmpdir, "Dockerfile")
        dockerfile_contents1 = read_ustring_from_utf8_file(dockerfile)
        dockerfile_contents2 = dockerfile_contents1.replace("-${ARCH}", "")
        if dockerfile_contents1 != dockerfile_contents2:
            logger.info(f"Removed -${{ARCH}} from {dockerfile}")

        write_ustring_to_utf8_file(
            dockerfile_contents2,
            new_dockerfile,
        )

        cmd = [
            "docker",
            "buildx",
            "build",
            "--platform",
            ",".join(platforms),
            "--push",
            "--metadata-file",
            metadata_file,
            "--tag",
            tag,
            *build_args_cl,
            *labels_cl,
        ]
        if nocache:
            cmd.append("--no-cache")
        if pull:
            cmd.append("--pull")
        cmd.extend(["--file", new_dockerfile])
        cmd.append(path)
        logger.info(" ".join(cmd))
        subprocess.check_call(cmd)

        contents = read_ustring_from_utf8_file(metadata_file)
        contents_j = json.loads(contents)
        image_id = contents_j["containerimage.digest"]

    return cast(DockerCompleteImageName, f"{tag}@{image_id}")


def add_digest_to_tag(tag: DockerCompleteImageName) -> DockerCompleteImageName:
    return cast(DockerCompleteImageName, f"{tag}@{get_manifest_digest(tag)}")


@lru_cache(maxsize=None)
def add_digest_to_tag_cached(tag: DockerCompleteImageName) -> DockerCompleteImageName:
    return add_digest_to_tag(tag)


def get_manifest_digest(tag: DockerCompleteImageName) -> str:
    cmd = ["docker", "buildx", "imagetools", "inspect", tag]
    res0 = subprocess.check_output(cmd)

    r = r"\nDigest:\s*(.*)\n"
    m = re.search(r, res0.decode())
    if m is None:
        msg = f"Cannot find the digest in string:\n{res0}"
        raise Exception(msg)
    sha = m.group(1)
    return sha
