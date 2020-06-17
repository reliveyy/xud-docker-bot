from requests import post
import logging


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
