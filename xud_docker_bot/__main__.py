import argparse
from yaml import safe_load

from .server import Server
from .config import Config

parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
parser.add_argument("--host")
parser.add_argument("--port", type=int)
args = parser.parse_args()

config = Config()

yml = safe_load(open("bot.yml"))

try:
    config.discord.token = yml["discord"]["token"]
except KeyError:
    pass

try:
    config.discord.channel = yml["discord"]["channel"]
except KeyError:
    pass

try:
    config.travis.api_token = yml["travis"]["api_token"]
except KeyError:
    pass

try:
    config.dockerhub.username = yml["dockerhub"]["username"]
except KeyError:
    pass

try:
    config.dockerhub.password = yml["dockerhub"]["password"]
except KeyError:
    pass

host = "0.0.0.0"
port = 8080

if hasattr(args, "host"):
    host = args.host

if hasattr(args, "port"):
    port = args.port

Server(config).run(host=host, port=port)
