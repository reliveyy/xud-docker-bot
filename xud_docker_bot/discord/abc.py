from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from ..context import Context


class BaseCog(commands.Cog):
    def __init__(self, context: Context):
        self.logger = logging.getLogger("xud_docker_bot.discord." + self.__class__.__name__)
        self.context = context
