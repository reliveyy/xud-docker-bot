from dataclasses import dataclass


@dataclass
class DiscordConfig:
    token: str = None
    channel: int = None


@dataclass
class TravisConfig:
    api_token: str = None


class Config:
    discord = DiscordConfig()
    travis = TravisConfig()
