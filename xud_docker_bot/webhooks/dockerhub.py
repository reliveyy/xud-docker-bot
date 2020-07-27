from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import humanize
from aiohttp import web

from .abc import Hook

if TYPE_CHECKING:
    pass


@dataclass
class Image:
    platform: str
    digest: str
    size: int
    branch: str
    revision: str
    travis_url: str
    app_revision: str


class DockerhubHook(Hook):
    def normalize_pusher(self, pusher):
        if pusher == "reliveyy":
            pusher = "Yang"
        elif pusher == "xubot":
            pusher = ":robot:"
        return pusher

    def inspect_tag(self, repo, tag):
        client = self.context.dockerhub_client
        try:
            j = client.get_tag(repo, tag)
            assert j
            result = []
            for img in j["images"]:
                platform = "{}/{}".format(img["os"], img["architecture"])
                digest = img["digest"]  # manifest digest
                size = img["size"]

                # TODO migrate to DockerhubClient#get_image -> DockerImage
                manifest = client.get_manifest(repo, digest)
                real_digest = manifest.payload["config"]["digest"]
                blob = client.get_blob(repo, real_digest)

                labels = blob.payload["config"]["Labels"]
                branch = labels.get("com.exchangeunion.image.branch", None)
                revision = labels.get("com.exchangeunion.image.revision", None)
                app_revision = labels.get("com.exchangeunion.application.revision", None)
                travis_url = labels.get("com.exchangeunion.image.travis", None)
                result.append(Image(platform, real_digest, size, branch, revision, travis_url, app_revision))
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to inspect tag: {repo} {tag}", e)

    def parse_tag(self, repo, tag):
        images = self.inspect_tag("exchangeunion/{}".format(repo), tag)
        return images

    async def handle(self, request: web.Request) -> web.Response:
        try:
            j = await request.json()
            repo = j["repository"]["name"]
            push_data = j["push_data"]
            pusher = self.normalize_pusher(push_data["pusher"])
            tag = push_data["tag"]
            images = self.parse_tag(repo, tag)

            msg = "%s pushed %s:**%s**" % (pusher, repo, tag.replace("__", r"\__"))
            for img in images:
                r1 = img.revision
                if r1:
                    r1 = r1[:5]
                else:
                    r1 = "N/A"

                r2 = img.app_revision
                if r2:
                    r2 = r2[:5]
                else:
                    r2 = "N/A"

                travis_url = img.travis_url
                if not travis_url:
                    travis_url = "N/A"

                msg += "\n**{}**: `{}` {}, xud-docker `{}`, app `{}`, build <{}>".format(
                    img.platform,
                    img.digest.replace("sha256:", "")[:5],
                    humanize.naturalsize(img.size, binary=True),
                    r1,
                    r2,
                    travis_url,
                )
            self.context.discord_template.publish_message(msg)
        except:
            self.logger.debug("Failed to process dockerhub webhook")
        return web.Response()
