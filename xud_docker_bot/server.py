from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from aiohttp import web

from .context import Context
from .web_handles import index
from .webhooks import DockerhubHook, GithubHook, TravisHook

if TYPE_CHECKING:
    from .config import Config


class Server:
    def __init__(self, config: Config):
        self.context = Context(config)
        self._logger = logging.getLogger("xud_docker_bot.Server")

    def run(self, host, port):
        self._logger.info("Starting...")
        loop = self.context.loop
        app = web.Application()
        app["context"] = self.context

        github_hook = GithubHook(self.context)

        app.add_routes([
            web.get("/", index),
            web.post("/webhooks/dockerhub", DockerhubHook(self.context).handle),
            web.post("/webhooks/github", github_hook.handle),
            web.post("/webhooks/travis", TravisHook(self.context).handle),
        ])
        runner = web.AppRunner(app)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, host=host, port=port)

        self._logger.info("HTTP Server start listening on %s:%d", host, port)

        token = self.context.config.discord.token
        assert token
        bot = self.context.discord_template.bot

        try:
            loop.run_until_complete(asyncio.gather(
                site.start(),
                bot.start(token),
                github_hook.process_queue()
            ))
        except KeyboardInterrupt:
            loop.run_until_complete(bot.logout())
        finally:
            loop.close()
