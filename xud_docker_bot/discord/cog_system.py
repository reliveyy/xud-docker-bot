from __future__ import annotations

from discord.ext.commands import command
from discord.ext.commands import Cog

from .abc import BaseCog


class SystemCog(BaseCog):
    @command()
    async def t1(self, ctx):
        message = await ctx.send("test!!!")
        for emoji in ('👍', '👎'):
            await message.add_reaction(emoji)

    # @Cog.listener()
    # async def on_reaction_add(self, reaction, user):
    #     pass
