from requests import post, get
import logging
from typing import List
import os
from subprocess import check_output, PIPE, CalledProcessError


class TravisClientError(Exception):
    pass


class TravisClient:
    def __init__(self, api_token):
        self._logger = logging.getLogger("xud_docker_bot.TravisClient")
        self.api_token = api_token
        self.repo = "ExchangeUnion%2Fxud-docker"
        self.api_url = "https://api.travis-ci.org"

    def trigger_travis_build(self, branch: str, message: str):
        r = post(f"{self.api_url}/repo/{self.repo}/requests", json={
            "request": {
                "message": message,
                "branch": branch,
            }
        }, headers={
            "Travis-API-Version": "3",
            "Authorization": "token " + self.api_token,
        })
        j = r.json()
        if j["@type"] == "error":
            raise TravisClientError(j["error_message"])
        self._logger.debug("Triggered %s build for branch %s: %s", self.repo, branch, r.text)

    def _convert_docker_platform_to_travis(self, platform: str):
        platform = platform.strip()
        platform = platform.lower()
        if platform == "linux/amd64":
            return "amd64"
        elif platform == "linux/arm64":
            return "arm64"
        else:
            raise RuntimeError("Cannot map Docker platform {} to Travis platform".format(platform))

    def trigger_travis_build2(
            self,
            branch: str,
            message: str,
            images: List[str],
            force: bool = False,
            platforms: List[str] = None):

        if force:
            script = "tools/push -f {}".format(" ".join(images))
        else:
            script = "tools/push {}".format(" ".join(images))

        if platforms:
            arch = [self._convert_docker_platform_to_travis(p) for p in platforms]
        else:
            arch = ["amd64", "arm64"]

        r = post(f"{self.api_url}/repo/{self.repo}/requests", json={
            "request": {
                "message": message,
                "branch": branch,
                "merge_mode": "replace",
                "config": {
                    "language": "python",
                    "python": "3.8",
                    "arch": arch,
                    "git": {
                        "depth": False,
                    },
                    "services": ["docker"],
                    "before_script": [
                        'echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin',
                    ],
                    "script": script
                }
            }
        }, headers={
            "Travis-API-Version": "3",
            "Authorization": "token " + self.api_token,
        })
        j = r.json()
        if j["@type"] == "error":
            raise TravisClientError(j["error_message"])
        remaining_requests = j["remaining_requests"]
        request_id = j["request"]["id"]
        self._logger.debug("Triggered %s build for branch %s: %s", self.repo, branch, r.text)
        return remaining_requests, request_id

    def get_request(self, request_id):
        r = get(f"{self.api_url}/repo/{self.repo}/request/{request_id}", headers={
            "Travis-API-Version": "3",
            "Authorization": "token " + self.api_token,
        })
        return r.json()

    def cancel_travis_build(self, build_id: str):
        r = post(f"{self.api_url}/build/{build_id}/cancel", headers={
            "Travis-API-Version": "3",
            "Authorization": "token " + self.api_token,
        })
        self._logger.debug("Canceled build: %s", build_id)

    def restart_travis_build(self, build_id: str):
        r = post(f"{self.api_url}/build/{build_id}/restart", headers={
            "Travis-API-Version": "3",
            "Authorization": "token " + self.api_token,
        })
        self._logger.debug("Restarted build: %s", build_id)
