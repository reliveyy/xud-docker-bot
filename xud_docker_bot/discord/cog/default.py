from __future__ import annotations

import humanize
import argparse
import logging

from discord import Embed
from discord.ext.commands import command, Context, group

from .abc import BaseCog
from .argparse import ArgumentParser, ArgumentError, CommandHelp
from xud_docker_bot.docker import DockerHubClient
from xud_docker_bot.build_service import BuildService, InvalidImage


logger = logging.getLogger(__name__)


class DefaultCog(BaseCog, name="Default Category"):
    def __init__(self, dockerhub: DockerHubClient, discord_channel_id: int, build_service: BuildService):
        self.build_parser = self._build_parser()
        self.debug_channel_id = 621384846475788290
        self.dockerhub = dockerhub
        self.discord_channel_id = discord_channel_id
        self.build_service = build_service

    @command()
    async def tags(self, ctx: Context, repo: str):
        repo = f"exchangeunion/{repo}"
        tags = await self.dockerhub.get_tags(repo)
        embed = Embed(title=f"{tags.count} tag(s) in {repo}")
        for t in tags.results:
            value = "Size: ~{}\nDigest: {}".format(humanize.naturalsize(t.full_size, binary=True), t.image_id)
            embed.add_field(name=t.name, value=value)
        await ctx.send(embed=embed)

    @command()
    async def remove(self, ctx: Context, image: str):
        raise NotImplementedError

    @command(brief="A test command")
    async def t1(self, ctx: Context):
        message = await ctx.send("test!!!")
        for emoji in ('👍', '👎'):
            await message.add_reaction(emoji)

    @command(brief="List bot pending jobs")
    async def jobs(self):
        raise NotImplementedError

    @group(brief="Inspect Travis-CI resources")
    async def inspect(self, ctx: Context):
        raise NotImplementedError

    @inspect.command()
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

    @staticmethod
    def _build_parser() -> ArgumentParser:
        parser = ArgumentParser(prog="build", add_help=False)

        parser.add_argument(
            "-h", "--help",
            action='help', default=argparse.SUPPRESS,
            help="show this help message")

        parser.add_argument("-b", "--branch", default="master", metavar="<branch>")
        parser.add_argument("-p", "--platform", action="append", metavar="<platform>")
        parser.add_argument("image", nargs="+")
        return parser

    @command()
    async def build(self, ctx: Context, *args):
        logger.debug("[Command] build: %r", args)

        channel = ctx.channel

        if channel.id != self.discord_channel_id and channel.id != self.debug_channel_id:
            logger.debug("Block the command comes from other channels: %r, %r", self.discord_channel_id, self.debug_channel_id)
            return

        full_command = "!build {}".format(" ".join(args))

        try:
            args = self.build_parser.parse_args(args)
            logger.debug("Parsed arguments: %r", args)
        except ArgumentError as e:
            title = "Argument Error"
            desc = str(e).capitalize()
            embed = Embed(title=title, description=desc, color=0xff0000)
            embed.add_field(name="Command", value=full_command, inline=False)
            embed.add_field(name="Usage", value=self.build_parser.format_usage(), inline=False)
            await ctx.send(embed=embed)
            return
        except CommandHelp:
            title = "Command Help `!build` :bookmark:"
            desc = """\
!build [**-b** __branch__] [**-p** __platform__] __image__ [__image__...]
!build **-h**
"""
            embed = Embed(title=title, description=desc, color=0xb7d8e8)
            embed.add_field(name="Options :gear:", value="""\
`-h/--help`
Show this help manual.                
            
`-b/--branch string`
Specify the branch of xud-docker to build. (default: master)

**`-p/--platform string`**
Build specified platform images. You could use this option multiple times. (default: -p linux/amd64 -p linux/arm64)

**`image`**
A valid image name (including the tag) in xud-docker **images** folder. E.g. __xud__, __xud:latest__, __xud:1.0.0__. If you do not specify the image tag, it will use **latest** by default.
""")
            embed.set_footer(text="◇ xud-docker-bot | v1.0.0.dev57")
            await ctx.send(embed=embed)
            return

        try:
            job = await self.build_service.build(branch=args.branch, platforms=args.platform, images=args.image, creator=ctx.author)
            title = "Job #%s" % job.id
            desc = full_command
            embed = Embed(title=title, description=desc, color=0x36ad5c)
            await ctx.send(embed=embed)
        except InvalidImage as e:
            title = "Invalid Image"
            desc = str(e)
            embed = Embed(title=title, description=desc, color=0xff0000)
            embed.add_field(name="Command", value=full_command, inline=False)
            embed.add_field(name="Usage", value=self.build_parser.format_usage(), inline=False)
            await ctx.send(embed=embed)
