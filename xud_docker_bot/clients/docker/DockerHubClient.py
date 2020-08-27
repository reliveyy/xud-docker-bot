from typing import Dict, Optional, List
from datetime import datetime

import requests

from .DockerRegistryClient import DockerRegistryClient
from .DockerImage import DockerImage
from .Tag import Tag


class DockerHubClient(DockerRegistryClient):
    def __init__(self, token_url: str, registry_url: str, hub_url: str):
        super().__init__(token_url=token_url, registry_url=registry_url)
        self.hub_url = hub_url

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
