import logging

fmt = "%(asctime)s.%(msecs)03d %(levelname)s %(process)d --- [%(threadName)s] %(name)s: %(message)s"
datefmt = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(level=logging.ERROR, filename="bot.log", format=fmt, datefmt=datefmt)
logging.getLogger("xud_docker_bot").setLevel(logging.DEBUG)
