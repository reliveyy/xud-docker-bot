import asyncio
from .clients import TravisClient, DockerhubClient
from .config import Config
from .discord import DiscordTemplate


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
