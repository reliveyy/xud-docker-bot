from __future__ import annotations
import argparse
from typing import TYPE_CHECKING
from asyncio import sleep

from discord.ext import commands
from discord.ext.commands import Context

from .abc import BaseCog
from ..clients import TravisClientError

if TYPE_CHECKING:
    pass


class ArgumentError(Exception):
    def __init__(self, message, usage):
        super().__init__(message)
        self.usage = usage


class ArgumentParser(argparse.ArgumentParser):
    """
    https://stackoverflow.com/questions/5943249/python-argparse-and-controlling-overriding-the-exit-status-code
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.register("action", "help", CustomHelpAction)

    def error(self, message):
        raise ArgumentError(message, self.format_usage())


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

# FIXME remove the hardcoded available_images
available_images = [
    "bitcoind",
    "litecoind",
    "geth",
    "lndbtc",
    "lndltc",
    "lndbtc-simnet",
    "lndltc-simnet",
    "connext",
    "xud",
    "arby",
    "boltz",
    "webui",
    "utils",
]


class TravisCog(BaseCog, name="Travis Category"):
    @commands.command(brief=BUILD_BRIEF, usage=BUILD_USAGE)
    async def build(self, ctx: Context, *args):
        if ctx.message.channel.id != self.context.config.discord.channel:
            return

        parser = ArgumentParser(prog="build", add_help=False)
        parser.add_argument("-b", "--branch", default="master", metavar="<branch>")
        parser.add_argument("-p", "--platform", action="append", metavar="<platform>")
        parser.add_argument("-f", "--force", action="store_true")
        parser.add_argument("image", nargs="+")
        cmd = ".build {}".format(" ".join(args))

        try:
            args = parser.parse_args(args)
        except ArgumentError as e:
            msg = "🚨 Failed to parse arguments for `%s`: %s\n%s" % (cmd, e, e.usage)
            await ctx.send(msg)
            return

        for image in args.image:
            if ":" in image:
                image = image.split(":")[0]
            if image not in available_images:
                msg = "🚨 Invalid image: " + image
                await ctx.send(msg)
                return

        try:
            client = self.context.travis_client
            remaining_requests, request_id = client.trigger_travis_build2(
                args.branch,
                "Triggered from Discord by {}".format(ctx.author),
                args.image,
                force=args.force,
                platforms=args.platform
            )
            msg = "✅ Successfully created build request `%s` for `%s` (remaining requests: %s)" % (request_id, cmd, remaining_requests)
            await ctx.send(msg)

            while True:
                await sleep(3)
                r = client.get_request(request_id)
                builds = r["builds"]
                if len(builds) > 0:
                    build_urls = []
                    for build in builds:
                        url = "https://travis-ci.org/github/ExchangeUnion/xud-docker/builds/%s" % build["id"]
                        build_urls.append(url)
                    msg = "✅ Successfully triggered builds for `%s`:\n%s" % (
                        cmd,
                        "\n".join(["<{}>".format(url) for url in build_urls])
                    )
                    await ctx.send(msg)
                    break

        except TravisClientError as e:
            msg = "🚨 Failed to create build request for `%s`: %s" % (cmd, e)
            await ctx.send(msg)

    @commands.command(brief="A shortcut command which equals to \".build -b master xud:latest\"")
    async def buildxudmaster(self, ctx: Context):
        if ctx.message.channel.id != self.context.config.discord.channel:
            return
        await self.build(ctx, "xud")
