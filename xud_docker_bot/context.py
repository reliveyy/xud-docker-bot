import asyncio
from asyncio.queues import Queue
from typing import List, Any
from datetime import datetime
from logging import getLogger
import os

from .clients import TravisClient, DockerhubClient
from .config import Config
from .discord import DiscordTemplate
from .xud_docker import XudDockerRepo


class BuildJob:
    def __init__(self, id: int, branch: str, platforms: List[str], images: List[str], creator: Any):
        self.id = id
        self.branch = branch
        self.platforms = platforms
        self.images = images
        self.creator = creator
        self.created_at = datetime.now()


class JobManager:
    def __init__(self, travis_client: TravisClient):
        self.queue = Queue()
        self.travis_client = travis_client
        self.logger = getLogger("xud_docker_bot.JobManager")
        self.count = 0

    async def create_build_job(self, branch: str, platforms: List[str], images: List[str], creator: Any):
        self.count = self.count + 1
        job = BuildJob(id=self.count, branch=branch, platforms=platforms, images=images, creator=creator)
        await self.queue.put(job)
        return job

    async def run(self):
        while True:
            job = await self.queue.get()
            if isinstance(job, BuildJob):
                client = self.travis_client
                remaining_requests, request_id = client.trigger_travis_build2(
                    job.branch,
                    "Triggered from Discord by {}.\nWill build {}.".format(job.creator, ", ".join(job.images)),
                    job.images,
                    force=False,
                    platforms=job.platforms
                )
                self.logger.debug("Created Travis request %s, remaining requests: %s", request_id, remaining_requests)


class Context:
    loop: asyncio.AbstractEventLoop
    travis_client: TravisClient
    discord_template: DiscordTemplate
    dockerhub_client: DockerhubClient

    def __init__(self, config: Config):
        self.config = config
        self.travis_client = TravisClient(config.travis.api_token)
        self.loop = asyncio.get_event_loop()
        self.discord_template = DiscordTemplate(self)
        self.dockerhub_client = DockerhubClient()

        self.job_manager = JobManager(self.travis_client)

        self.loop.create_task(self.job_manager.run())

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

        repo_dir = os.path.expanduser("~/.xud-docker-bot/xud-docker")
        self.xud_docker = XudDockerRepo(repo_dir, self.dockerhub_client)
