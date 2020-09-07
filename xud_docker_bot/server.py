from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from aiohttp import web
import os

from .web_handles import index
from .webhooks import DockerhubHook, GithubHook, TravisHook
from .discord import DiscordClient
from .docker import DockerHubClient
from .build_service import BuildService
from .xud_docker import XudDockerRepo
from .travis import TravisClient

if TYPE_CHECKING:
    from .config import Config

__all__ = (
    "Server"
)


logger = logging.getLogger(__name__)


class Server:
    def __init__(self, config: Config):
        self.config = config
        # self.context = Context(config)

    @property
    def host(self) -> str:
        return self.config.host

    @property
    def port(self) -> int:
        return self.config.port

    async def run(self):

        logger.info("Starting...")

        # Start
        # 1. HTTP server provides webhooks
        # 2. Discord client (bot)
        # 3. Github webhook process queue -> Job Manager (process backend jobs, like build job, analyze job, clean job)
        # github_hook.process_queue()

        dockerhub = DockerHubClient(self.config.dockerhub.username, self.config.dockerhub.password)

        repo_dir = os.path.expanduser("~/.xud-docker-bot/xud-docker")
        xud_docker = XudDockerRepo(repo_dir, dockerhub)
        travis = TravisClient(self.config.travis.api_token)
        build_service = BuildService(travis, xud_docker)

        discord = DiscordClient(
            self.config.discord.token,
            self.config.discord.channel,
            dockerhub,
            build_service,
        )

        app = web.Application()

        # app["context"] = self.context

        routes = [
            web.get("/", index),
            web.post("/webhooks/dockerhub", DockerhubHook(travis, discord, dockerhub, xud_docker, build_service).handle),
            web.post("/webhooks/github", GithubHook(travis, discord, dockerhub, xud_docker, build_service).handle),
            web.post("/webhooks/travis", TravisHook(travis, discord, dockerhub, xud_docker, build_service).handle),
        ]

        app.add_routes(routes)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=self.host, port=self.port)
        logger.info("HTTP Server start listening on %s:%d", self.host, self.port)

        try:
            await asyncio.gather(
                site.start(),
                discord.start(),
                build_service.run(),
            )
        finally:
            await asyncio.gather(
                site.stop(),
                discord.stop(),
            )

        logger.info("end")
