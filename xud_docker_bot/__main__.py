from . import Config, Server
import asyncio

config = Config()
server = Server(config)
try:
    asyncio.run(server.run())
except KeyboardInterrupt:
    pass
