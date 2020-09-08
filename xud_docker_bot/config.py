from __future__ import annotations

from dataclasses import dataclass
import sys
import os


__all__ = (
    "Config"
)


@dataclass
class DiscordConfig:
    token: str = None
    channel: int = None


@dataclass
class TravisConfig:
    api_token: str = None


@dataclass
class DockerhubConfig:
    username: str = None
    password: str = None


class Config:
    host: str
    port: int

    def __init__(self):
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--host")
        parser.add_argument("--port", type=int)
        parser.add_argument("--config-file", default="bot.yml")
        parser.add_argument("--log-file", default="bot.log")
        args = parser.parse_args()

        self.host = args.host or "0.0.0.0"
        self.port = args.port or 8080

        from yaml import safe_load
        yml = safe_load(open("bot.yml"))

        self.discord = DiscordConfig()
        self.discord.token = yml["discord"]["token"]
        self.discord.channel = yml["discord"]["channel"]

        self.travis = TravisConfig()
        self.travis.api_token = yml["travis"]["api_token"]

        self.dockerhub = DockerhubConfig()
        self.dockerhub.username = yml["dockerhub"]["username"]
        self.dockerhub.password = yml["dockerhub"]["password"]

        import logging
        fmt = "%(asctime)s.%(msecs)03d %(levelname)s %(process)d --- [%(threadName)s] %(name)s: %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        logging.basicConfig(level=logging.ERROR, format=fmt, datefmt=datefmt, stream=sys.stdout)
        logging.getLogger("xud_docker_bot").setLevel(logging.DEBUG)

        self.home_dir = os.path.expanduser("~/.xud-docker-bot")
        self.repos_dir = os.path.join(self.home_dir, "repos")
