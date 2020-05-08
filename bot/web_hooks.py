import logging
from dataclasses import dataclass
from typing import AnyStr
import humanize
from aiohttp import web
from requests import get, post
from urllib.parse import parse_qs
import json

from .discord_bot import bot

logger = logging.getLogger(__name__)


@dataclass
class Image:
    platform: AnyStr
    digest: AnyStr
    size: int
    branch: AnyStr
    revision: AnyStr
    travis_url: AnyStr


def get_token(repo):
    try:
        r = get(f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repo}:pull")
        return r.json()["token"]
    except Exception as e:
        raise RuntimeError("Failed to get Docker registry API token", e)


def get_blob(token, repo, digest):
    try:
        url = f"https://registry-1.docker.io/v2/{repo}/blobs/{digest}"
        r = get(url, headers={
            "Authorization": f"Bearer {token}"
        })
        payload = r.json()
        return payload
    except Exception as e:
        raise RuntimeError(f"Failed to get Docker registry blob: {repo} {digest}", e)


def get_submanifest(token, repo, digest):
    try:
        url = f"https://registry-1.docker.io/v2/{repo}/manifests/{digest}"
        r = get(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.docker.distribution.manifest.v2+json, "
                      "application/vnd.docker.distribution.manifest.list.v2+json, "
                      "application/vnd.docker.distribution.manifest.v1+json"
        })
        payload = r.json()
        digest = payload["config"]["digest"]
        return digest, get_blob(token, repo, digest)
    except Exception as e:
        raise RuntimeError(f"Failed to get Docker registry manifest: {repo} {digest}", e)


def inspect_tag(repo, tag):
    try:
        url = f"https://hub.docker.com/v2/repositories/{repo}/tags/{tag}"
        r = get(url)
        j = r.json()
        result = []
        for img in j["images"]:
            platform = "{}/{}".format(img["os"], img["architecture"])
            digest = img["digest"]  # manifest digest
            size = img["size"]
            real_digest, blob = get_submanifest(get_token(repo), repo, digest)
            labels = blob["config"]["Labels"]
            branch = labels.get("com.exchangeunion.image.branch", None)
            revision = labels.get("com.exchangeunion.image.revision", None)
            travis_url = labels.get("com.exchangeunion.image.travis", None)
            result.append(Image(platform, real_digest, size, branch, revision, travis_url))
        return result
    except Exception as e:
        raise RuntimeError(f"Failed to inspect tag: {repo} {tag}", e)


def parse_tag(repo, tag):
    images = inspect_tag("exchangeunion/{}".format(repo), tag)
    return images


def normalize_pusher(pusher):
    if pusher == "reliveyy":
        pusher = "Yang"
    elif pusher == "xubot":
        pusher = ":robot:"
    return pusher


async def dockerhub(request: web.Request):
    j = await request.json()
    repo = j["repository"]["name"]
    push_data = j["push_data"]
    pusher = normalize_pusher(push_data["pusher"])
    tag = push_data["tag"]
    images = parse_tag(repo, tag)

    msg = "%s pushed tag %s:**%s**" % (pusher, repo, tag.replace("__", r"\__"))
    for img in images:
        msg += "\n• **Platform:** {}\n   **Digest:** `{}`\n   **Size:** ~{}\n   **Branch:** {}\n   **Revision:** `{}`".format(
            img.platform,
            img.digest,
            humanize.naturalsize(img.size, binary=True),
            img.branch,
            img.revision,
        )
        if img.travis_url:
            msg += "\n   **Travis Build:** <{}>".format(img.travis_url)
    logger.info(msg)
    channel = bot.get_channel(request.app["ctx"].discord.channel)  # xud-docker-bot
    bot.loop.create_task(channel.send(msg))
    return web.Response()


def find_all_branches_in_xud_docker(repo, branch):
    # TODO get all branches which are affected by the changes of <branch> in <repo>
    if repo == "reliveyy/xud":
        return ["xud-latest"]
    return []


def trigger_travis_build_for_branch(branch, api_token):
    r = post("https://api.travis-ci.org/repo/ExchangeUnion%2Fxud-docker/requests", json={
        "request": {
            "branch": "xud-latest"
        }
    }, headers={
        "Travis-API-Version": "3",
        "Authorization": "token " + api_token
    })
    logger.info("Triggered ExchangeUnion/xud-docker build for branch {}: {}".format(branch, r.text))


async def handle_upstream_repo_update(repo, branch, api_token):
    if repo == "reliveyy/xud":
        branches = find_all_branches_in_xud_docker(repo, branch)
        for b in branches:
            trigger_travis_build_for_branch(b, api_token)


async def github(request):
    api_token = request.app["ctx"].travis.api_token
    j = await request.json()
    try:
        repo = j["repository"]["full_name"]
        if repo == "reliveyy/xud":
            ref = j["ref"]
            branch = ref.replace("refs/heads/", "")
            logger.info("github push %s %s", repo, branch)
            await handle_upstream_repo_update(repo, branch, api_token)
        else:
            logger.info("Ignore GitHub %s webhook", repo)
    except Exception as e:
        raise RuntimeError(e, "Failed to parse github webhook: {}".format(j))
    return web.Response()


async def travis(request: web.Request):
    t = await request.text()
    params = parse_qs(t)
    j = json.loads(params["payload"][0])
    print(j)
    repo = j["repository"]["name"]
    if repo == "xud-docker":
        build_id = j["id"]
        number = j["number"]
        result = j["result_message"]
        branch = j["branch"]
        commit = j["commit"]
        commit_message = j["message"]
        msg = f"🏗️ Travis build #{number}: **{result.lower()}**"
        msg += f"\n**Link:** <https://travis-ci.org/github/ExchangeUnion/xud-docker/builds/{build_id}>"
        msg += f"\n**Branch:** {branch}"
        msg += f"\n**Commit:** `{commit}`"
        msg += f"\n**Message:** {commit_message}"
        msg += f"\n**Tests:** N/A"
        channel = bot.get_channel(request.app["ctx"].discord.channel)  # xud-docker-bot
        bot.loop.create_task(channel.send(msg))
    return web.Response()


async def travis_test_reports(request):
    pass
