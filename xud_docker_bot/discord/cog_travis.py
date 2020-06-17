from __future__ import annotations
from typing import TYPE_CHECKING

from discord.ext import commands
from .abc import BaseCog
from discord.ext.commands import Context
from ..clients import TravisClientError

if TYPE_CHECKING:
    pass


class TravisCog(BaseCog, name="Travis Category"):
    @commands.command(brief="Trigger a Travis build for specific branch", usage="""-- Trigger a Travis build for specific branch

SYNOPSIS
    build <branch>
      
DESCRIPTION
    The branch parameter is the existing branch name of Travis ExchangeUnion/xud-docker repository. We normally trigger master build because it uses xud master branch in the Dockerfile.
""")
    async def build(self, ctx: Context, branch: str):
        assert branch
        try:
            self.context.travis_client.trigger_travis_build(branch, "Triggered from Discord by {}".format(ctx.author))
        except TravisClientError as e:
            await ctx.send("**Error:** %s" % e)

    @commands.command(brief="A shortcut command which equals to \".build master\"")
    async def buildxudmaster(self, ctx: Context):
        await self.build(ctx, branch="master")
