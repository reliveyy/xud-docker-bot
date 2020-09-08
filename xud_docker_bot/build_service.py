from __future__ import annotations
from typing import List, Any, Optional
from asyncio.queues import Queue
from datetime import datetime
import logging
from git import Repo


logger = logging.getLogger(__name__)


class InvalidImage(Exception):
    pass


class BuildJob:
    def __init__(self, id: int, branch: str, platforms: List[str], images: List[str], travis_message: str):
        self.id = id
        self.branch = branch
        self.platforms = platforms
        self.images = images
        self.travis_message = travis_message
        self.created_at = datetime.now()


class BuildService:
    def __init__(self, travis, xud_docker):
        self.travis = travis
        self.xud_docker = xud_docker

        self.available_images = {
            "bitcoind": ["https://github.com/bitcoin/bitcoin"],
            "litecoind": ["https://github.com/litecoin-project/litecoin"],
            "geth": ["https://github.com/ethereum/go-ethereum"],
            "lndbtc": ["https://github.com/lightningnetwork/lnd"],
            "lndltc": ["https://github.com/ltcsuite/lnd"],
            "lndbtc-simnet": ["https://github.com/lightningnetwork/lnd"],
            "lndltc-simnet": ["https://github.com/ltcsuite/lnd"],
            "connext": ["https://github.com/connext/rest-api-client"],
            "xud": ["https://github.com/ExchangeUnion/xud"],
            "arby": ["https://github.com/ExchangeUnion/market-maker-tools"],
            "boltz": ["https://github.com/BoltzExchange/boltz-lnd"],
            "webui": ["https://github.com/ExchangeUnion/xud-webui-poc", "https://github.com/ExchangeUnion/xud-socketio"],
            "utils": ["https://github.com/ExchangeUnion/xud-docker"]
        }

        self.queue = Queue()
        self.job_index = 0

    async def _create_build_job(self, branch: str, platforms: List[str], images: List[str], travis_message: str):
        self.job_index = self.job_index + 1
        job = BuildJob(id=self.job_index, branch=branch, platforms=platforms, images=images, travis_message=travis_message)
        await self.queue.put(job)
        return job

    async def build(self, branch: str, platforms: List[str], images: List[str], creator: Any) -> BuildJob:
        for image in images:
            if ":" in image:
                image = image.split(":")[0]
            if image not in self.available_images:
                raise InvalidImage(image)
        travis_message = "Triggered from Discord by {}.\nWill build {}.".format(creator, ", ".join(images))
        job = await self._create_build_job(branch=branch, platforms=platforms, images=images, travis_message=travis_message)
        return job

    async def auto_build(self, repo: str, ref: str, commit_message: Optional[str]):
        if repo == "ExchangeUnion/xud-docker":
            git_ref, images = self.xud_docker.get_modified_images(ref)
            if ref.startswith("refs/heads/"):
                branch = ref.replace("refs/heads/", "")
            else:
                raise RuntimeError("Failed to parse branch from reference %s" % ref)

            platforms = ["linux/amd64", "linux/arm64"]
            travis_message = git_ref.commit_message
            job = await self._create_build_job(branch=branch, platforms=platforms, images=images, travis_message=travis_message)
            return job
        else:
            if repo == "ExchangeUnion/xud":
                image = "xud"
            elif repo == "ExchangeUnion/market-maker-tools":
                image = "arby"
            elif repo == "BoltzExchange/boltz-lnd":
                image = "boltz"
            else:
                raise RuntimeError("Unexpected repo name: " + repo)

            if ref.startswith("refs/heads/"):
                branch = ref.replace("refs/heads/", "")
            else:
                raise RuntimeError("Unexpected ref: " + ref)

            branches = self.xud_docker.get_affected_branches(image, branch)
            if len(branches) == 0:
                return
            for b in branches:
                travis_msg = "%s(%s): %s" % (repo, branch, commit_message)
                images = [f"{image}:latest"]
                platforms = ["linux/amd64", "linux/arm64"]
                await self.travis.trigger_travis_build(b, travis_msg, )
                travis_message = "Triggered from GitHub {} branch {} updates.\n{}\nWill build {}.".format(repo, branch, commit_message, ", ".join(images))
                job = await self._create_build_job(branch=b, platforms=platforms, images=images, travis_message=travis_message)
                return job

    async def run(self):
        while True:
            job = await self.queue.get()
            if len(job.images) == 0:
                continue
            if isinstance(job, BuildJob):
                remaining_requests, request_id = await self.travis.trigger_travis_build(
                    job.branch,
                    job.travis_message,
                    job.images,
                    platforms=job.platforms
                )
                logger.debug("Created Travis request %s, remaining requests: %s", request_id, remaining_requests)
            elif job == "EXIT":
                break

    async def find_job(self, message_id: int):
        pass
