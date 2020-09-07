from __future__ import annotations
from typing import TYPE_CHECKING
from abc import abstractmethod

if TYPE_CHECKING:
    from aiohttp import web
    from xud_docker_bot.travis import TravisClient
    from xud_docker_bot.discord import DiscordClient
    from xud_docker_bot.docker import DockerHubClient
    from xud_docker_bot.xud_docker import XudDockerRepo
    from xud_docker_bot.build_service import BuildService


class Hook:
    def __init__(
        self,
        travis: TravisClient,
        discord: DiscordClient,
        dockerhub: DockerHubClient,
        xud_docker: XudDockerRepo,
        build_service: BuildService
    ):
        self.travis = travis
        self.discord = discord
        self.dockerhub = dockerhub
        self.xud_docker = xud_docker
        self.build_service = build_service

    @abstractmethod
    async def handle(self, request: web.Request) -> web.Response:
        pass
