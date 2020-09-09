from __future__ import annotations

import logging
from typing import TYPE_CHECKING
import traceback

from discord import Embed
from discord.ext.commands import Cog, Context, CommandError


if TYPE_CHECKING:
    from ..context import Context
    from ..config import Config


class BaseCog(Cog):
    def __init__(self, context: Context):
        self.logger = logging.getLogger("xud_docker_bot.discord." + self.__class__.__name__)
        self.context = context

    @property
    def config(self) -> Config:
        return self.context.config

    @property
    def job_manager(self):
        return self.context.job_manager

    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError):
        title = "Internal Error"
        error = error.__cause__
        tb = traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__)
        desc = tb[-1]
        embed = Embed(title=title, description=desc, color=0xff0000)
        name = tb[0]
        tb = tb[1:-1]
        lines = []
        for line in tb:
            line = line.replace("  File", "File")
            line = line.replace("    ", "```python\n")
            line = line + "\n```"
            lines.append(line)
        embed.add_field(name=name, value="\n".join(lines))
        embed.set_footer(text="◇ xud-docker-bot | v1.0.0.dev57")

        # for m in ctx.channel.members:
        #     if m.name == "bitdancer"
        # mention the bot author
        await ctx.send(content="<@280196677988777986>", embed=embed)
