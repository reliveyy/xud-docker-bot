import asyncio
from .config import Config
from .clients import TravisTemplate, DockerTemplate
from .discord import DiscordTemplate


class Context:
    loop: asyncio.AbstractEventLoop
    travis_template: TravisTemplate
    docker_template: DockerTemplate
    discord_template: DiscordTemplate

    def __init__(self, config: Config):
        self.config = config
        self.loop = asyncio.get_event_loop()
        self.travis_template = TravisTemplate(config.travis.api_token)
        self.docker_template = DockerTemplate()
        self.discord_template = DiscordTemplate(self)
