from __future__ import annotations
from typing import TYPE_CHECKING

from discord.ext import commands
from .abc import BaseCog
from discord.ext.commands import Context

if TYPE_CHECKING:
    pass


class TravisCog(BaseCog, name="Travis Commands"):
    @commands.command(brief="Trigger a Travis build for specific branch.", usage="""
NAME
      build -- Trigger a Travis build for specific branch
SYNOPSIS
      build <branch>
""")
    async def build(self, ctx: Context, branch: str):
        assert branch
        self.context.travis_client.trigger_travis_build(branch, "Triggered from Discord by {}".format(ctx.author))

    @commands.command(brief="A shortcut command which equals to \".build master\"")
    async def buildxudmaster(self, ctx: Context):
        await self.build(ctx, branch="master")
