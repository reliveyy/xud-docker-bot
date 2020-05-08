import argparse
from yaml import safe_load

from . import Server, Context

parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
parser.add_argument("--host")
parser.add_argument("--port", type=int)
parser.add_argument("--discord-token")
parser.add_argument("--discord-channel")
parser.add_argument("--travis-api-token")
args = parser.parse_args()

ctx = Context()

yml = safe_load(open("bot.yml"))

try:
    ctx.discord.token = yml["discord"]["token"]
except KeyError:
    pass

try:
    ctx.discord.channel = yml["discord"]["channel"]
except KeyError:
    pass

try:
    ctx.travis.api_token = yml["travis"]["api_token"]
except KeyError:
    pass


if hasattr(args, "discord_token"):
    ctx.discord.token = getattr(args, "discord_token")

if hasattr(args, "discord_channel"):
    ctx.discord.channel = getattr(args, "discord_channel")

if hasattr(args, "travis_api_token"):
    ctx.travis.api_token = getattr(args, "travis_api_token")

host = "0.0.0.0"
port = 8080

if hasattr(args, "host"):
    host = args.host

if hasattr(args, "port"):
    port = args.port

Server(ctx).run(host=host, port=port)
