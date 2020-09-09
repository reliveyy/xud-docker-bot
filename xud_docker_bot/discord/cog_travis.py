from __future__ import annotations
import argparse
from typing import TYPE_CHECKING

from discord import Embed
from discord.ext.commands import Context, command

from .abc import BaseCog

if TYPE_CHECKING:
    pass


class ArgumentError(Exception):
    pass


class CommandHelp(Exception):
    pass


class _HelpAction(argparse.Action):
    def __init__(self,
                 option_strings,
                 dest=argparse.SUPPRESS,
                 default=argparse.SUPPRESS,
                 help=None):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        raise CommandHelp(parser.format_help())


class ArgumentParser(argparse.ArgumentParser):
    """
    https://stackoverflow.com/questions/5943249/python-argparse-and-controlling-overriding-the-exit-status-code
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register("action", "help", _HelpAction)

    def error(self, message):
        raise ArgumentError(message)


BUILD_HELP = """\
SYNOPSIS
    build [-f] [-p <platform>] [-b <branch>] <image:tag> [<image:tag>...]
      
DESCRIPTION
    This command builds specific images of a branch of xud-docker on Travis-CI.
    
    The options are as follows:
    -b, --branch     Specify the branch of xud-docker to build. (default: master)
    -p, --platform   Build specified platform images. (default equals to -p linux/amd64 -p linux/arm64)
    -f, --force      Force build images
"""

BUILD_BRIEF = "Trigger a Travis build for Docker images"
BUILD_USAGE = "-- %s\n\n%s" % (BUILD_BRIEF, BUILD_HELP)


class TravisCog(BaseCog, name="Travis Category"):
    def __init__(self, context):
        super().__init__(context)
        self.build_parser = self._help_parser()
        self.debug_channel_id = 621384846475788290

    @staticmethod
    def _help_parser() -> ArgumentParser:
        parser = ArgumentParser(prog="build", add_help=False)

        parser.add_argument(
            "-h", "--help",
            action='help', default=argparse.SUPPRESS,
            help="show this help message")

        parser.add_argument("-b", "--branch", default="master", metavar="<branch>")
        parser.add_argument("-p", "--platform", action="append", metavar="<platform>")
        parser.add_argument("image", nargs="+")
        return parser

    @command(brief=BUILD_BRIEF, usage=BUILD_USAGE)
    async def build(self, ctx: Context, *args):
        self.logger.debug("[Command] build: %r", args)

        channel = ctx.channel

        if channel.id != self.config.discord.channel and channel.id != self.debug_channel_id:
            self.logger.debug("Block the command comes from other channels: %r, %r", self.config.discord.channel, self.debug_channel_id)
            return

        full_command = "!build {}".format(" ".join(args))

        try:
            args = self.build_parser.parse_args(args)
            self.logger.debug("Parsed arguments: %r", args)
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

        for image in args.image:
            if ":" in image:
                image = image.split(":")[0]
            if image not in self.context.available_images:
                title = "Invalid Image"
                desc = image
                embed = Embed(title=title, description=desc, color=0xff0000)
                embed.add_field(name="Command", value=full_command, inline=False)
                embed.add_field(name="Usage", value=self.build_parser.format_usage(), inline=False)
                await ctx.send(embed=embed)
                return

        job = await self.job_manager.create_build_job(branch=args.branch, platforms=args.platform, images=args.image, creator=ctx.author)

        title = "Job #%s" % job.id
        desc = full_command
        embed = Embed(title=title, description=desc, color=0x36ad5c)
        await ctx.send(embed=embed)
