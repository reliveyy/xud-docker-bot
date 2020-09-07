from __future__ import annotations

from aiohttp.client import ClientSession
import requests
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime

from .schema import ManifestPage, ManifestPageSchema, RepositoryPage, RepositoryPageSchema

__all__ = (
    "DockerHubClient"
)


@dataclass
class Resource:
    digest: str
    payload: Dict



@dataclass
class DockerImage:
    digest: str
    revision: str
    app_revision: str
    created_at: datetime


class DockerRegistryClientError(Exception):
    pass


class DockerRegistryClient:
    def __init__(self, token_url: str, registry_url: str):
        self.token_url = token_url
        self.registry_url = registry_url

    def get_token(self, repo):
        try:
            r = requests.get("{}?service=registry.docker.io&scope=repository:{}:pull".format(self.token_url, repo))
            return r.json()["token"]
        except Exception as e:
            raise DockerRegistryClientError("Failed to get token for repository: {}".format(repo)) from e

    def get_manifest(self, repo: str, tag: str) -> Optional[Resource]:
        try:
            url = f"{self.registry_url}/v2/{repo}/manifests/{tag}"
            media_types = [
                "application/vnd.docker.distribution.manifest.list.v2+json",
                "application/vnd.docker.distribution.manifest.v2+json",
                "application/vnd.docker.distribution.manifest.v1+json",
            ]
            r = requests.get(url, headers={
                "Authorization": "Bearer " + self.get_token(repo),
                "Accept": ",".join(media_types),
            })
            if r.status_code == requests.codes.ok:
                payload = r.json()
                digest = r.headers.get("Docker-Content-Digest")
                return Resource(digest=digest, payload=payload)
            elif r.status_code == requests.codes.not_found:
                return None
            else:
                r.raise_for_status()
        except Exception as e:
            raise DockerRegistryClientError("Failed to get manifest: {}:{}".format(repo, tag)) from e

    def get_blob(self, repo: str, digest: str) -> Optional[Resource]:
        try:
            url = f"{self.registry_url}/v2/{repo}/blobs/{digest}"
            r = requests.get(url, headers={
                "Authorization": "Bearer {}".format(self.get_token(repo))
            })
            if r.status_code == requests.codes.ok:
                payload = r.json()
                digest = r.headers.get("Docker-Content-Digest")
                return Resource(digest=digest, payload=payload)
            elif r.status_code == requests.codes.not_found:
                return None
        except Exception as e:
            raise DockerRegistryClientError("Failed to get blob: {}:{}".format(repo, digest)) from e


class DockerHubClient:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.url = "https://hub.docker.com/v2"
        self.token = None
        token_url="https://auth.docker.io/token"
        registry_url="https://registry-1.docker.io"
        self.registry_client = DockerRegistryClient(token_url, registry_url)

    def get_tag(self, repo: str, tag: str) -> Optional[Dict]:
        url = f"{self.url}/repositories/{repo}/tags/{tag}"
        r = requests.get(url)
        if r.status_code == requests.codes.ok:
            return r.json()
        elif r.status_code == requests.codes.not_found:
            return None
        else:
            r.raise_for_status()

    async def get_tags(self, repo: str, page_size: int = 10, page: int = 1) -> ManifestPage:
        async with ClientSession() as session:
            url = f"{self.url}/repositories/{repo}/tags"
            async with session.get(url, params={
                "page_size": page_size,
                "page": page,
            }) as resp:
                j = await resp.json()
                return ManifestPageSchema().load(j)

    async def get_all_tags(self, repo: str):
        page_size = 100
        i = 1
        page = await self.get_tags(repo, page_size=page_size, page=i)
        total = page.count
        result = page.results
        while i * page_size < total:
            i = i + 1
            page = await self.get_tags(repo, page_size=page_size, page=i)
            result.extend(page.results)
        return result

    async def get_token(self) -> str:
        if not self.token:
            async with ClientSession() as session:
                url = f"{self.url}/users/login"
                r = await session.post(url, json={
                    "username": self.username,
                    "password": self.password,
                })
                j = await r.json()
                self.token = j["token"]
        return self.token

    async def remove_tag(self, repo: str, tag: str):
        async with ClientSession() as session:
            url = f"{self.url}/repositories/{repo}/tags/{tag}"
            token = await self.get_token()
            r = await session.delete(url, headers={
                "Authorization": f"JWT {token}"
            })
            return await r.json()

    async def get_repos(self, user: str = None, page_size: int = 10, page: int = 1) -> RepositoryPage:
        async with ClientSession() as session:
            if not user:
                user = self.username
            url = f"{self.url}/repositories/{user}?page_size=100"
            token = await self.get_token()
            r = await session.get(url, headers={
                "Authorization": f"JWT {token}"
            }, params={
                "page_size": page_size,
                "page": page,
            })
            j = await r.json()
            return RepositoryPageSchema().load(j)

    async def logout(self, token: str):
        raise NotImplementedError

    def _get_single_manifest(self, r1, repo):
        digest = r1.payload["config"]["digest"]

        r2 = self.registry_client.get_blob(repo, digest)
        labels = r2.payload["config"]["Labels"]

        revision = labels.get("com.exchangeunion.image.revision", None)
        app_revision = labels.get("com.exchangeunion.application.revision", None)

        # FIXME created_at
        return DockerImage(digest=digest, revision=revision, app_revision=app_revision, created_at=datetime.now())

    def get_image(self, repo, tag) -> Optional[DockerImage]:
        r1 = self.registry_client.get_manifest(repo, tag)
        if not r1:
            return None

        schema_version = r1.payload["schemaVersion"]
        if schema_version != 2:
            raise RuntimeError("Unsupported schema version %s" % schema_version)

        media_type = r1.payload["mediaType"]

        if media_type == "application/vnd.docker.distribution.manifest.v2+json":
            return self._get_single_manifest(r1, repo)
        elif media_type == "application/vnd.docker.distribution.manifest.list.v2+json":
            for manifest in r1.payload["manifests"]:
                digest = manifest["digest"]
                p = manifest["platform"]
                arch = p["architecture"]
                if arch == "amd64":
                    r2 = self.registry_client.get_manifest(repo, digest)
                    return self._get_single_manifest(r2, repo)
