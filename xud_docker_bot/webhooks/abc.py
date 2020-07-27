from __future__ import annotations
from typing import TYPE_CHECKING
from abc import abstractmethod
import logging

if TYPE_CHECKING:
    from aiohttp import web
    from ..context import Context


class Hook:
    def __init__(self, context: Context):
        self.logger = logging.getLogger("xud_docker_bot.webhooks." + self.__class__.__name__)
        self.context = context

    @abstractmethod
    async def handle(self, request: web.Request) -> web.Response:
        pass
