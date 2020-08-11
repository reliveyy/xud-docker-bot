import logging
import sys

fmt = "%(asctime)s.%(msecs)03d %(levelname)s %(process)d --- [%(threadName)s] %(name)s: %(message)s"
datefmt = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(level=logging.ERROR, format=fmt, datefmt=datefmt, filename="bot.log")
logging.getLogger("xud_docker_bot").setLevel(logging.DEBUG)
