from .context import Context
import asyncio
from aiohttp import web
import logging
import sys

from .web_handles import index, dockerhub, github, travis, travis_test_reports
from .discord_bot import bot

logging.basicConfig(level=logging.ERROR, stream=sys.stdout)
logging.getLogger("bot").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


class Server:
    def __init__(self, ctx: Context):
        self.ctx = ctx

    def run(self, host, port):
        loop = self.ctx.loop
        app = web.Application()
        app["ctx"] = self.ctx
        app.add_routes([
            web.get("/", index),
            web.post("/webhooks/dockerhub", dockerhub),
            web.post("/webhooks/github", github),
            web.post("/webhooks/travis", travis),
            web.post("/webhooks/travis/test-reports", travis_test_reports)
        ])
        runner = web.AppRunner(app)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, host=host, port=port)

        logger.info("HTTP Server start listening on %s:%d", host, port)

        token = self.ctx.discord.token
        assert token

        try:
            loop.run_until_complete(asyncio.gather(site.start(), bot.start(self.ctx.discord.token)))
        except KeyboardInterrupt:
            loop.run_until_complete(bot.logout())
        finally:
            loop.close()
