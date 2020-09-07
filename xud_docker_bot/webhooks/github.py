from collections import namedtuple
from subprocess import CalledProcessError
import asyncio
import logging

from aiohttp import web
from discord import Embed

from .abc import Hook

Event = namedtuple("Event", ["repo", "ref", "commit_message"])


logger = logging.getLogger(__name__)


class GithubHook(Hook):

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
            return
        branch_list = ", ".join(branches)
        lines = message.splitlines()
        first_line = lines[0]
        msg = "{} branch **{}** was pushed ({}). Will trigger builds for {}." \
            .format(repo, branch, first_line, branch_list)
        await self.discord.send(msg)
        for b in branches:
            travis_msg = "%s(%s): %s" % (repo, branch, message)
            await self.travis.trigger_travis_build(b, travis_msg, [f"{image}:latest"])

    async def process_queue(self):
        while True:
            ref = await self.queue.get()
            self.logger.debug("Process xud-docker %s", ref)
            try:
                client = self.context.travis_template
                git_ref, images = self.xud_docker.get_modified_images(ref)
                if len(images) > 0:
                    if ref.startswith("refs/heads/"):
                        branch = ref.replace("refs/heads/", "")
                    else:
                        raise RuntimeError("Failed to parse branch from reference %s" % ref)

                    lines = git_ref.commit_message.splitlines()
                    first_line = lines[0].strip()
                    if len(images) == 0:
                        build_msg = "Will build **no** images."
                    else:
                        build_msg = "Will build images: {}.".format(", ".join(images))
                    msg = "ExchangeUnion/xud-docker branch **{}** was pushed ({}). {}" \
                        .format(branch, first_line, build_msg)
                    self.context.discord_template.publish_message(msg)

                    remaining_requests, request_id = client.trigger_travis_build2(branch, git_ref.commit_message,
                                                                                  images)
                    self.logger.debug("Created Travis build request %s for images: %s (%s request(s) left)",
                                      request_id, ", ".join(images), remaining_requests)
            except Exception as e:
                p = e
                while p:
                    if isinstance(p, CalledProcessError):
                        self.logger.error("Failed to execute command\n$ %s\n%s", p.cmd, p.output.decode().strip())
                        break
                    p = e.__cause__
                self.logger.exception("Failed to process xud-docker %s", ref)

    async def handle_xud_docker_update(self, ref: str):
        if "tag" in ref:
            return
        branch = ref.replace("refs/heads/", "")
        self.build_service.auto_build(repo, ref, commit_message)
        await self.queue.put(ref)

    async def _parse_request(self, request: web.Request) -> Event:
        j = await request.json()
        repo = j["repository"]["full_name"]
        ref = j["ref"]
        msg = None
        try:
            msg = j["head_commit"]["message"]
        except:
            pass

        return Event(repo, ref, msg)

    async def _handle(self, event):
        try:
            ref = event.ref
            repo = event.repo
            msg = event.commit_message

            job = await self.build_service.auto_build(repo, ref, msg)
            title = "Job #%s" % job.id
            desc = "Auto-build for **{}** branch **{}**.\n\n{}".format(repo, ref, msg)
            embed = Embed(title=title, description=desc, color=0x36ad5c)
            await self.discord.send(embed=embed)


            # if ref.startswith("refs/heads/"):
            #     branch = ref.replace("refs/heads/", "")
            # else:
            #     raise RuntimeError("Failed to parse branch from reference %s" % ref)
            #
            # if repo == "ExchangeUnion/xud":
            #     await self.handle_upstream_update(repo, branch, msg)
            # elif repo == "ExchangeUnion/market-maker-tools":
            #     await self.handle_upstream_update(repo, branch, msg)
            # elif repo == "BoltzExchange/boltz-lnd":
            #     await self.handle_upstream_update(repo, branch, msg)
            # elif repo == "ExchangeUnion/xud-docker":
            #     await self.handle_xud_docker_update(ref)
        except:
            logger.exception("Failed to process GitHub webhook")

    async def handle(self, request: web.Request) -> web.Response:
        event = await self._parse_request(request)
        asyncio.create_task(self._handle(event))
        return web.Response()
