from xud_docker_bot.clients import TravisClient


def test1():
    client = TravisClient(api_token="***REMOVED***")
    result = client.get_builds_of_github_repo("ExchangeUnion/xud-docker")
    print(result)


def test2():
    print("world")