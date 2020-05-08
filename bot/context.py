from dataclasses import dataclass
import asyncio


@dataclass
class Discord:
    token: str = None
    channel: int = None


@dataclass
class Travis:
    api_token: str = None


@dataclass
class Context:
    discord: Discord = Discord()
    travis: Travis = Travis()
    loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
