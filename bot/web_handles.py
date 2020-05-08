from aiohttp import web
from .web_hooks import dockerhub, github, travis, travis_test_reports

__all__ = ["dockerhub", "github", "travis", "travis_test_reports"]


async def index(request):
    return web.Response(text="Welcome to xud-docker-bot!")
