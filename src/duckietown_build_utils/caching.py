import os
import sqlite3
import traceback
from datetime import datetime
from typing import Tuple

from zuper_commons.timing import now_utc
from . import logger
from .types import (
    DockerImageDigest,
    DockerImageID,
    DockerOrganizationName,
    DockerRegistryName,
    DockerRepositoryName,
    DockerTag,
)

__all__ = ["DockerCaching", "docker_caching"]


class DockerCaching:
    def __init__(self, fn: str):
        self.fn = fn
        self.inited = False
        self.cannot_use = None

    def _check_inited(self):
        if self.inited:
            return

        if not os.path.exists(self.fn):
            msg = "We are creating for the first time"
            logger.info(msg, fn=self.fn)
            dn = os.path.dirname(self.fn)
            if not os.path.exists(dn):
                os.makedirs(dn)
        try:
            self.conn = sqlite3.connect(self.fn)
        except sqlite3.OperationalError as e:
            logger.error("Cannot open file", fn=self.fn, tn=traceback.format_exc())
            self.cannot_use = True
            self.inited = True
            return
        self.cannot_use = False
        self.c = self.conn.cursor()

        sqls = [
            """CREATE TABLE IF NOT EXISTS tags
(
    registry  text      not null,
    org       text      not null,
    repo      text      not null,
    tag       text      not null,
    image_id  text      not null,
    digest    text      not null,
    last_push timestamp not null,

    UNIQUE (registry, org, repo, tag)
); """,
            """CREATE TABLE IF NOT EXISTS images
(
    registry  text      not null,
    org       text      not null,
    repo      text      not null,
    image_id  text      not null,
    digest    text      not null,
    last_push timestamp not null,
    UNIQUE (registry, org, repo, image_id)
);

                """,
        ]
        for sql in sqls:
            self.c.execute(sql)
        self.conn.commit()
        self.inited = True

    def get_last_image_push(
        self,
        registry: DockerRegistryName,
        org: DockerOrganizationName,
        repo: DockerRepositoryName,
        image_id: DockerImageID,
    ) -> Tuple[datetime, DockerImageDigest]:
        """Raises KeyError"""

        assert image_id is not None
        self._check_inited()
        if self.cannot_use:
            raise KeyError()
        sql = """-- noinspection SqlResolveForFile

select last_push, digest
from images
where registry = ?
  and org = ?
  and repo = ?
  and image_id = ?
           """
        self.c.execute(
            sql,
            (
                registry,
                org,
                repo,
                image_id,
            ),
        )
        data = self.c.fetchone()

        if not data:
            raise KeyError()
        else:
            last_push, digest = data
            return parse_sqlite_time(last_push), digest

    def mark_image_pushed(
        self,
        registry: DockerRegistryName,
        org: DockerOrganizationName,
        repo: DockerRepositoryName,
        image_id: DockerImageID,
        digest: DockerImageDigest,
    ):
        assert digest is not None
        self._check_inited()
        if self.cannot_use:
            return
        sql = """-- noinspection SqlResolveForFile

insert into images (registry, org, repo, image_id, digest, last_push)
values (?, ?, ?, ?, ?, ?)
on conflict(registry, org, repo, image_id) do update
    set last_push = excluded.last_push,
        digest    = excluded.digest
        """
        self.c.execute(sql, (registry, org, repo, image_id, digest, now_utc()))
        self.conn.commit()

    def get_last_tag_push_any(
        self,
        registry: DockerRegistryName,
        org: DockerOrganizationName,
        repo: DockerRepositoryName,
        tag: DockerTag,
    ) -> Tuple[datetime, DockerImageID, DockerImageDigest]:
        """Raises KeyError"""
        assert tag is not None
        self._check_inited()
        if self.cannot_use:
            raise KeyError()

        sql = """-- noinspection SqlResolveForFile
    select digest, image_id, last_push
    from tags
    where registry = ?
      and org = ?
      and repo = ?
      and tag = ?
                  """
        self.c.execute(sql, (registry, org, repo, tag))
        data = self.c.fetchone()

        if not data:
            raise KeyError()
        else:
            digest, image_id, last_push = data
            return parse_sqlite_time(last_push), image_id, digest

    def get_last_tag_push(
        self,
        registry: DockerRegistryName,
        org: DockerOrganizationName,
        repo: DockerRepositoryName,
        tag: DockerTag,
        image_id: DockerImageID,
    ) -> Tuple[datetime, DockerImageDigest]:
        """Raises KeyError"""
        assert tag is not None
        self._check_inited()
        if self.cannot_use:
            raise KeyError()

        sql = """-- noinspection SqlResolveForFile
select digest, last_push
from tags
where registry = ?
  and org = ?
  and repo = ?
  and tag = ?
  and image_id = ?
              """
        self.c.execute(sql, (registry, org, repo, tag, image_id))
        data = self.c.fetchone()

        if not data:
            raise KeyError()
        else:
            digest, last_push = data
            return parse_sqlite_time(last_push), digest

    def mark_tag_pushed(
        self,
        registry: DockerRegistryName,
        org: DockerOrganizationName,
        repo: DockerRepositoryName,
        tag: DockerTag,
        image_id: DockerImageID,
        digest: DockerImageDigest,
    ):
        assert tag is not None
        assert digest is not None

        self._check_inited()
        if self.cannot_use:
            return
        sql = """-- noinspection SqlResolveForFile

insert into tags (registry, org, repo, tag, image_id, digest, last_push)
values (?, ?, ?, ?, ?, ?, ?)
on conflict(registry, org, repo ,tag) do update
    set last_push = excluded.last_push,
        digest    = excluded.digest,
        image_id  = excluded.image_id
           """
        self.c.execute(sql, (registry, org, repo, tag, image_id, digest, now_utc()))
        self.conn.commit()


def parse_sqlite_time(s: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f%z")
    except Exception as e:
        msg = f"Cannot parse date {s!r}"
        raise ValueError(msg) from e


fn = os.path.expanduser("~/.dt-caches/docker-caching2.sqlite")
docker_caching = DockerCaching(fn=fn)
