import os

from aiohttp import web
from collections import namedtuple
from asyncio.queues import Queue
from subprocess import CalledProcessError

from .abc import Hook
from xud_docker_bot.xud_docker import XudDockerRepo


Event = namedtuple("Event", ["repo", "ref", "commit_message"])


class GithubHook(Hook):
    def __init__(self, context):
        super().__init__(context)
        repo_dir = os.path.expanduser("~/.xud-docker-bot/xud-docker")
        registry_client = context.dockerhub_client
        self.xud_docker = XudDockerRepo(repo_dir, registry_client)
        self.queue = Queue()

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
        self.context.discord_template.publish_message(msg)
        for b in branches:
            travis_msg = "%s(%s): %s" % (repo, branch, message)
            self.context.travis_client.trigger_travis_build2(b, travis_msg, [f"{image}:latest"])

    async def process_queue(self):
        while True:
            ref = await self.queue.get()
            self.logger.debug("Process xud-docker %s", ref)
            try:
                client = self.context.travis_client
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

                    remaining_requests, request_id = client.trigger_travis_build2(branch, git_ref.commit_message, images)
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

    async def handle_xud_docker_update(self, ref):
        self.context.discord_template.publish_message("Submit xud-docker %s build task" % ref)
        await self.queue.put(ref)

    async def _parse_request(self, request: web.Request) -> Event:
        try:
            j = await request.json()
            repo = j["repository"]["full_name"]
            ref = j["ref"]
            msg = None
            try:
                msg = j["head_commit"]["message"]
            except:
                pass

            return Event(repo, ref, msg)

        except Exception as e:
            raise RuntimeError("Failed to parse GitHub webhook") from e

    async def handle(self, request: web.Request) -> web.Response:
        try:
            event = await self._parse_request(request)

            ref = event.ref
            repo = event.repo
            msg = event.commit_message

            if ref.startswith("refs/heads/"):
                branch = ref.replace("refs/heads/", "")
            else:
                raise RuntimeError("Failed to parse branch from reference %s" % ref)

            if repo == "ExchangeUnion/xud":
                await self.handle_upstream_update(repo, branch, msg)
            elif repo == "ExchangeUnion/market-maker-tools":
                await self.handle_upstream_update(repo, branch, msg)
            elif repo == "BoltzExchange/boltz-lnd":
                await self.handle_upstream_update(repo, branch, msg)
            elif repo == "ExchangeUnion/xud-docker":
                await self.handle_xud_docker_update(ref)
        except:
            # TODO save failed payload for further analyzing
            self.logger.exception("Failed to process GitHub webhook")

        return web.Response()
