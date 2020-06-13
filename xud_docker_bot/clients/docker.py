from dataclasses import dataclass
from typing import Dict, Optional, List
from collections import namedtuple

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


