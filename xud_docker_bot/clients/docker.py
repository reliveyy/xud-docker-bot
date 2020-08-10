from dataclasses import dataclass
from typing import Dict, Optional, List
from collections import namedtuple
from datetime import datetime

import requests


@dataclass
class Resource:
    digest: str
    payload: Dict


class DockerRegistryClientError(Exception):
    pass


Tag = namedtuple("Tag", ["name", "size"])


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


@dataclass
class DockerImage:
    digest: str
    revision: str
    app_revision: str
    created_at: datetime


class DockerhubClient(DockerRegistryClient):
    def __init__(self):
        super().__init__(token_url="https://auth.docker.io/token", registry_url="https://registry-1.docker.io")
        self.hub_url = "https://hub.docker.com/v2"

    def get_tag(self, repo: str, tag: str) -> Optional[Dict]:
        url = f"{self.hub_url}/repositories/{repo}/tags/{tag}"
        r = requests.get(url)
        if r.status_code == requests.codes.ok:
            return r.json()
        elif r.status_code == requests.codes.not_found:
            return None
        else:
            r.raise_for_status()

    def get_tags(self, repo) -> List[Tag]:
        tags = []
        url = f"https://hub.docker.com/v2/repositories/{repo}/tags"
        while True:
            j = requests.get(url).json()
            url = j["next"]
            if not url:
                break
            for item in j["results"]:
                tags.append(Tag(item["name"], item["full_size"]))
        return tags

    def _get_single_manifest(self, r1, repo):
        digest = r1.payload["config"]["digest"]

        r2 = self.get_blob(repo, digest)
        labels = r2.payload["config"]["Labels"]

        revision = labels.get("com.exchangeunion.image.revision", None)
        app_revision = labels.get("com.exchangeunion.application.revision", None)

        # FIXME created_at
        return DockerImage(digest=digest, revision=revision, app_revision=app_revision, created_at=datetime.now())

    def get_image(self, repo, tag) -> Optional[DockerImage]:
        r1 = self.get_manifest(repo, tag)
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
                    r2 = self.get_manifest(repo, digest)
                    return self._get_single_manifest(r2, repo)

    def login(self, username, password) -> str:
        r = requests.post("https://hub.docker.com/v2/users/login", json={
            "username": username,
            "password": password,
        })
        if r.status_code == 200:
            return r.json()["token"]
        else:
            raise RuntimeError("Failed to login")

    def logout(self, token) -> None:
        r = requests.post("https://hub.docker.com/v2/logout", headers={
            "Authorization": f"JWT {token}"
        })
        if r.status_code == 200:
            if r.json()["detail"] != "Logged out":
                raise RuntimeError("Failed to logout")
        else:
            raise RuntimeError("Failed to logout")

    def remove_tag(self, token, repo, tag) -> None:
        r = requests.delete(f"https://hub.docker.com/v2/repositories/{repo}/tags/{tag}", headers={
            "Authorization": f"JWT {token}"
        })
        if r.status_code != 204:
            raise RuntimeError("Failed to remove {}:{}".format(repo, tag))
