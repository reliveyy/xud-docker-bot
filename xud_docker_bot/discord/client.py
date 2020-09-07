from __future__ import annotations

from discord import Reaction, User
from discord.ext.commands import Bot
import logging

from .cog import DefaultCog
from xud_docker_bot.docker import DockerHubClient
from xud_docker_bot.build_service import BuildService


__all__ = (
    "DiscordClient"
)


logger = logging.getLogger(__name__)


class DiscordClient(Bot):
    def __init__(
        self,
        token: str,
        notification_channel_id: int,
        dockerhub: DockerHubClient,
        build_service: BuildService
    ):
        super().__init__(command_prefix="!", help_command=None)

        self.token = token
        self.notification_channel_id = notification_channel_id
        self.dockerhub = dockerhub
        self.build_service = build_service

        self.channel = None

        default_cog = DefaultCog(dockerhub, notification_channel_id, build_service)
        self.add_cog(default_cog)

    async def on_ready(self):
        logger.info('%s has connected to Discord!', self.user)
        self.channel = self.get_channel(self.notification_channel_id)

    async def on_reaction_add(self, reaction: Reaction, user: User):
        if reaction.me:
            return

        job = self.build_service.find_job(message_id=reaction.message.id)
        if job and isinstance(job, BuildJob):
            if reaction.emoji == '🚫':
                #context.travis_template.cancel_travis_build(build_id)
                # job_manager.get_job(build_id=build_id)
                # job_manager.enqueue(CancelBuildJob(build_id))
                await job.cancel()
            elif reaction.emoji == '🔄':
                #context.travis_template.restart_travis_build(build_id)
                # job_manager.enqueue(RestartBuildJob(build_id))
                await job.restart()

    async def start(self):
        logger.info("Starting Discord client")
        await super().start(self.token)

    async def stop(self):
        logger.info("Shutting down Discord client")
        await super().logout()

    async def send(self, *args, **kwargs):
        return await self.channel.send(*args, **kwargs)
