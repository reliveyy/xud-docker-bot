from __future__ import annotations

from discord.ext.commands import Context, group, command
from discord import Embed

from .abc import BaseCog


class SystemCog(BaseCog):
    @command(brief="A test command")
    async def t1(self, ctx: Context):
        message = await ctx.send("test!!!")
        for emoji in ('👍', '👎'):
            await message.add_reaction(emoji)

    @command(brief="List bot pending jobs")
    async def jobs(self):
        raise NotImplementedError

    @group(brief="Inspect Travis-CI resources")
    # TODO safe group
    async def inspect(self, ctx: Context):
        raise NotImplementedError

    @inspect.command()
    # TODO safe group command
    async def travis(self, ctx: Context):
        await ctx.send("inspect travis")

    @command(brief="Release a new xud-docker version")
    async def release(self, ctx: Context):
        raise NotImplementedError

    @command()
    async def ping(self, ctx: Context):
        await ctx.send("pong!")

    @command()
    async def help(self, ctx: Context):
        title = "Command Help :bookmark:"
        desc = """This is the frontpage of all available commands. You can use `!help command` or `!command -h` to get a detailed help manual for that command."""
        embed = Embed(title=title, description=desc, color=0xb7d8e8)
        embed.add_field(name="!build", value="Manually build images of xud-docker repository. E.g. `!build xud`.", inline=False)
        embed.add_field(name="!ping", value="Ping me. I will send back `pong!` as a response.", inline=False)
        embed.set_footer(text="◇ xud-docker-bot | v1.0.0.dev57")
        await ctx.send(embed=embed)
