from __future__ import annotations

import os
from typing import TYPE_CHECKING

from aiohttp import web
from .abc import Hook
from ..xud_docker import XudDockerRepo

if TYPE_CHECKING:
    pass


class GithubHook(Hook):
    def __init__(self, context):
        super().__init__(context)
        self.xud_docker = XudDockerRepo(os.path.expanduser("~/.xud-docker-bot/xud-docker"))

    async def handle_upstream_update(self, repo, branch, message):
        if repo == "ExchangeUnion/xud":
            image = "xud"
        elif repo == "ExchangeUnion/market-maker-tools":
            image = "arby"
        elif repo == "BoltzExchange/boltz-lnd":
            image = "boltz"
        else:
            raise RuntimeError("Unsupported repository: " + repo)

        branches = self.xud_docker.get_affected_branches(image, branch)
        if len(branches) == 0:
            branch_list = "nothing"
        else:
            branch_list = ", ".join(branches)
        lines = message.splitlines()
        first_line = lines[0]
        msg = "{} branch **{}** was pushed ({}). Will trigger builds for {}." \
            .format(repo, branch, first_line, branch_list)
        self.context.discord_template.publish_message(msg)
        for b in branches:
            travis_msg = "%s(%s): %s" % (repo, branch, message)
            self.context.travis_client.trigger_travis_build2(b, travis_msg, [f"{image}:latest"])

    async def handle_xud_docker_update(self, branch, msg):
        client = self.context.travis_client
        images = self.xud_docker.get_modified_images(branch)
        if len(images) > 0:
            remaining_requests, request_id = client.trigger_travis_build2(branch, msg, images)
            self.logger.debug("Created Travis build request %s for images: %s (%s request(s) left)", request_id, ", ".join(images), remaining_requests)

    async def handle(self, request: web.Request) -> web.Response:
        j = await request.json()
        try:
            repo = j["repository"]["full_name"]
            if repo == "ExchangeUnion/xud":
                ref = j["ref"]
                branch = ref.replace("refs/heads/", "")
                msg = j["head_commit"]["message"]
                self.logger.debug("github push %s %s: %s", repo, branch, msg)
                await self.handle_upstream_update(repo, branch, msg)
            elif repo == "ExchangeUnion/market-maker-tools":
                ref = j["ref"]
                branch = ref.replace("refs/heads/", "")
                msg = j["head_commit"]["message"]
                self.logger.debug("github push %s %s: %s", repo, branch, msg)
                await self.handle_upstream_update(repo, branch, msg)
            elif repo == "BoltzExchange/boltz-lnd":
                ref = j["ref"]
                branch = ref.replace("refs/heads/", "")
                msg = j["head_commit"]["message"]
                self.logger.debug("github push %s %s: %s", repo, branch, msg)
                await self.handle_upstream_update(repo, branch, msg)
            elif repo == "ExchangeUnion/xud-docker":
                ref = j["ref"]
                branch = ref.replace("refs/heads/", "")
                msg = j["head_commit"]["message"]
                self.logger.debug("github push %s %s: %s", repo, branch, msg)
                await self.handle_xud_docker_update(branch, msg)
            else:
                self.logger.debug("Ignore GitHub %s webhook", repo)
        except:
            self.logger.exception("Failed to handle github webhook: %r", j)
        return web.Response()
