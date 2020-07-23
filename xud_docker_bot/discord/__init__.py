from __future__ import annotations
from typing import TYPE_CHECKING

from discord.ext import commands
import logging
import re

from .cog_system import SystemCog
from .cog_dockerhub import DockerhubCog
from .cog_travis import TravisCog

if TYPE_CHECKING:
    from ..context import Context


__all__ = ["DiscordTemplate"]


class DiscordTemplate:
    def __init__(self, context: Context):
        self._logger = logging.getLogger("xud_docker_bot.DiscordTemplate")
        bot = commands.Bot(command_prefix='.')

        @bot.event
        async def on_ready():
            self._logger.info('%s has connected to Discord!', bot.user)
            self._channel = bot.get_channel(context.config.discord.channel)  # xud-docker-bot

        @bot.event
        async def on_reaction_add(reaction, user):
            if user.name == "xud-docker-bot":
                return
            content = reaction.message.content
            p = re.compile("^.*builds/(.+)>$")
            lines = content.splitlines()
            if len(lines) <= 1:
                return
            m = p.match(lines[1])
            if m:
                build_id = m.group(1)
                if reaction.emoji == '🚫':
                    context.travis_client.cancel_travis_build(build_id)
                elif reaction.emoji == '🔄':
                    context.travis_client.restart_travis_build(build_id)

        bot.add_cog(DockerhubCog(context))
        bot.add_cog(TravisCog(context))
        bot.add_cog(SystemCog(context))

        self.bot = bot
        self._channel = None

    def publish_message(self, message: str):
        self.bot.loop.create_task(self._channel.send(message))

    async def publish_message_async(self, message: str):
        return await self._channel.send(message)
