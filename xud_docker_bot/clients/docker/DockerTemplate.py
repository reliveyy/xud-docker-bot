from typing import Optional, Dict, List

from .DockerImage import DockerImage
from .DockerHubClient import DockerHubClient
from .DockerTemplateError import DockerTemplateError
from .Tag import Tag
from .Resource import Resource


class DockerTemplate:
    def __init__(self):
        self._client = DockerHubClient(
            token_url="https://auth.docker.io/token",
            registry_url="https://registry-1.docker.io",
            hub_url="https://hub.docker.com/v2"
        )

    def get_image(self, repo: str, tag: str) -> Optional[DockerImage]:
        try:
            return self._client.get_image(repo, tag)
        except Exception as e:
            raise DockerTemplateError from e

    def get_tag(self, repo: str, tag: str) -> Optional[Dict]:
        try:
            return self._client.get_tag(repo, tag)
        except Exception as e:
            raise DockerTemplateError from e

    def get_tags(self, repo: str) -> List[Tag]:
        try:
            return self._client.get_tags(repo)
        except Exception as e:
            raise DockerTemplateError from e

    def login(self, username: str, password: str) -> str:
        try:
            return self._client.login(username, password)
        except Exception as e:
            raise DockerTemplateError from e

    def logout(self, token: str) -> None:
        try:
            self._client.logout(token)
        except Exception as e:
            raise DockerTemplateError from e

    def remove_tag(self, token: str, repo: str, tag: str) -> None:
        try:
            self._client.remove_tag(token, repo, tag)
        except Exception as e:
            raise DockerTemplateError from e

    def get_manifest(self, repo: str, tag: str) -> Optional[Resource]:
        try:
            return self._client.get_manifest(repo, tag)
        except Exception as e:
            raise DockerTemplateError from e

    def get_blob(self, repo: str, digest: str) -> Optional[Resource]:
        try:
            return self._client.get_blob(repo, digest)
        except Exception as e:
            raise DockerTemplateError from e
