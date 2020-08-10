from requests import post, get
import logging
from typing import List
import asyncio
from asyncio import sleep
from dataclasses import dataclass


class TravisClientError(Exception):
    pass


# Travis-CI build and job states
# created queued received started passed failed errored canceled ready
# https://github.com/travis-ci/travis.rb/blob/8e5ef45d61dce201c1cd12e5f494e4b4bc5dbe63/lib/travis/client/states.rb#L6

# Travis-CI request states
# approved rejected


@dataclass
class Job:
    job_id: int
    build_id: int
    state: str
    log: str


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

    async def tracking_jobs(self, request_id):
        self._logger.debug("Start tracking jobs of request %s", request_id)
        builds = []
        while True:
            await sleep(3)
            r = self.get_request(request_id)
            state = r["state"]
            if state == "finished":
                for build in r["builds"]:
                    builds.append(build["id"])
                break
        self._logger.debug("Request %s builds: %s", request_id, ", ".join(map(str, builds)))

        # request -> builds -> jobs
        jobs = []
        for build in builds:
            r = self.get_build(build)
            for job in r["jobs"]:
                job_id = job["id"]
                jobs.append(Job(job_id=job_id, build_id=build, state=None, log=None))
        self._logger.debug("Request %s jobs: %s", request_id, ", ".join(
            [f"{job.job_id}({job.build_id})" for job in jobs]))

        while True:
            finished_jobs = 0
            for job in jobs:
                if job.state in ["passed", "failed", "errored", "canceled"]:
                    finished_jobs = finished_jobs + 1
                    continue
                r = self.get_job(job.job_id)
                job.state = r["state"]
                self._logger.debug("Job %s state: %s", job.job_id, job.state)
                if job.state == "errored":
                    job.log = self.get_job_log(job.job_id)
            if finished_jobs == len(jobs):
                break
            await sleep(3)
        self._logger.debug("Finished tracking jobs of request %s", request_id)

    def trigger_travis_build2(
            self,
            branch: str,
            commit_message: str,
            images: List[str],
            force: bool = False,
            platforms: List[str] = None):

        script = "tools/push {}".format(" ".join(images))

        if platforms:
            arch = [self._convert_docker_platform_to_travis(p) for p in platforms]
        else:
            arch = ["amd64", "arm64"]

        payload = {
            "request": {
                "message": commit_message,
                "branch": branch,
                "merge_mode": "replace",
                "config": {
                    "language": "python",
                    "python": "3.8",
                    "arch": arch,
                    "services": ["docker"],
                    "before_script": [
                        'echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin',
                    ],
                    "script": script
                }
            }
        }

        # TODO remove this backward compatibility workaround
        if branch != "no-force" and not branch.startswith("dummy"):
            config = payload["request"]["config"]
            config["git"] = {
                "depth": False
            }

        r = post(f"{self.api_url}/repo/{self.repo}/requests", json=payload, headers={
            "Travis-API-Version": "3",
            "Authorization": "token " + self.api_token,
        })
        j = r.json()
        if j["@type"] == "error":
            raise TravisClientError(j["error_message"])
        remaining_requests = j["remaining_requests"]
        request_id = j["request"]["id"]
        self._logger.debug("Triggered %s build for branch %s", self.repo, branch)

        asyncio.get_running_loop().create_task(self.tracking_jobs(request_id))

        return remaining_requests, request_id

    def get_request(self, request_id):
        r = get(f"{self.api_url}/repo/{self.repo}/request/{request_id}", headers={
            "Travis-API-Version": "3",
            "Authorization": "token " + self.api_token,
        })
        return r.json()

    def get_build(self, build_id):
        r = get(f"{self.api_url}/build/{build_id}", headers={
            "Travis-API-Version": "3",
        })
        return r.json()

    def get_job(self, job_id):
        r = get(f"{self.api_url}/job/{job_id}", headers={
            "Travis-API-Version": "3",
        })
        return r.json()

    def get_job_log(self, job_id):
        r = get(f"{self.api_url}/job/{job_id}/log.txt", headers={
            "Travis-API-Version": "3",
        })
        return r.text

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

    def get_builds_of_github_repo(self, repo):
        repo = repo.replace("/", "%2F")
        r = get(f"{self.api_url}/repo/github/{repo}/builds", headers={
            "Travis-API-Version": "3",
            "Authorization": "token " + self.api_token,
        })
        return r.json()

