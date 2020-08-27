from typing import List
from .TravisClient import TravisClient
from .TravisTemplateError import TravisTemplateError


class TravisTemplate:
    def __init__(self, api_token: str):
        self._client = TravisClient(api_token)

    def trigger_travis_build(self, branch: str, message: str):
        try:
            return self._client.trigger_travis_build(branch, message)
        except Exception as e:
            raise TravisTemplateError from e

    async def tracking_jobs(self, request_id: str):
        try:
            await self._client.tracking_jobs(request_id)
        except Exception as e:
            raise TravisTemplateError from e

    def trigger_travis_build2(
            self,
            branch: str,
            commit_message: str,
            images: List[str],
            force: bool = False,
            platforms: List[str] = None):
        try:
            return self._client.trigger_travis_build2(branch, commit_message, images, force, platforms)
        except Exception as e:
            raise TravisTemplateError from e

    def get_request(self, request_id):
        try:
            return self._client.get_request(request_id)
        except Exception as e:
            raise TravisTemplateError from e

    def get_build(self, build_id):
        try:
            return self._client.get_build(build_id)
        except Exception as e:
            raise TravisTemplateError from e

    def get_job(self, job_id):
        try:
            return self._client.get_job(job_id)
        except Exception as e:
            raise TravisTemplateError from e

    def get_job_log(self, job_id):
        try:
            return self._client.get_job_log(job_id)
        except Exception as e:
            raise TravisTemplateError from e

    def cancel_travis_build(self, build_id: str):
        try:
            return self._client.cancel_travis_build(build_id)
        except Exception as e:
            raise TravisTemplateError from e

    def restart_travis_build(self, build_id: str):
        try:
            return self._client.restart_travis_build(build_id)
        except Exception as e:
            raise TravisTemplateError from e

    def get_builds_of_github_repo(self, repo):
        try:
            return self._client.get_builds_of_github_repo(repo)
        except Exception as e:
            raise TravisTemplateError from e
