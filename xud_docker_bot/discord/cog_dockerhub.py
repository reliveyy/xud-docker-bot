from __future__ import annotations

from discord.ext import commands
import humanize

from .abc import BaseCog


class DockerhubCog(BaseCog, name="DockerHub Category"):
    @commands.command()
    async def tags(self, ctx, name: str):
        assert name
        tags = self.context.dockerhub_client.get_tags(f"exchangeunion/{name}")
        msg = "Repository **exchangeunion/{}** has **{}** tag(s) in total.".format(name, len(tags))
        await ctx.send(msg)
        for t in tags:
            self.logger.debug("Iterating tag in %s repo: %r", name, t)
            await ctx.send(f"• `{t.name}`  ~{humanize.naturalsize(t.size, binary=True)}")
