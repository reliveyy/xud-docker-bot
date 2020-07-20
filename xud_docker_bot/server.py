from __future__ import annotations
from typing import TYPE_CHECKING

import asyncio
from aiohttp import web
import logging
import sys

from .web_handles import index
from .web_hooks import DockerhubHook, GithubHook, TravisHook
from .context import Context

if TYPE_CHECKING:
    from .config import Config

logging.basicConfig(level=logging.ERROR, stream=sys.stdout)
logging.getLogger("bot").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


class Server:
    def __init__(self, config: Config):
        self.context = Context(config)

    def run(self, host, port):
        loop = self.context.loop
        app = web.Application()
        app["context"] = self.context
        app.add_routes([
            web.get("/", index),
            web.post("/webhooks/dockerhub", DockerhubHook(self.context).handle),
            web.post("/webhooks/github", GithubHook(self.context).handle),
            web.post("/webhooks/travis", TravisHook(self.context).handle),
        ])
        runner = web.AppRunner(app)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, host=host, port=port)

        logger.info("HTTP Server start listening on %s:%d", host, port)

        token = self.context.config.discord.token
        assert token
        bot = self.context.discord_template.bot

        try:
            loop.run_until_complete(asyncio.gather(site.start(), bot.start(token)))
        except KeyboardInterrupt:
            loop.run_until_complete(bot.logout())
        finally:
            loop.close()
