from xud_docker_bot.docker import DockerHubClient
import asyncio
import pytest
from yaml import safe_load


@pytest.fixture
def client():
    with open("/Users/yy/work/xu/xud-docker-bot/bot.yml") as f:
        y = safe_load(f)
        username = y["dockerhub"]["username"]
        password = y["dockerhub"]["password"]
        client = DockerHubClient(username, password)
        return client


@pytest.mark.asyncio
async def test_get_tags(client):
    page = await client.get_tags("reliveyy/foo")
    print(page)
    print(len(page.results))
    for item in page.results:
        print(item.name)


@pytest.mark.asyncio
async def test_get_all_tags(client):
    result = await client.get_all_tags("reliveyy/foo")
    print(result)


@pytest.mark.asyncio
async def test_get_token(client):
    result = await client.get_token()
    print(result)


@pytest.mark.asyncio
async def test_get_repos(client):
    r = await client.get_repos()
    # r = await client.get_repos(user="exchangeunion")
    print(r)


@pytest.mark.asyncio
async def test_remove_tag(client):
    r = await client.remove_tag("reliveyy/foo", "latest")
    print(r)
