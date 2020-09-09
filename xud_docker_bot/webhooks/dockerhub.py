from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from discord import Embed

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
    manifest_digest: str


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
                result.append(Image(platform, real_digest, size, branch, revision, travis_url, app_revision, manifest_digest=digest))
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
            self.logger.debug("DockerHub tag %s pushed", tag)

            if tag.endswith("__x86_64"):
                tag1 = tag.replace("__x86_64", "")
            elif tag.endswith("__aarch64"):
                tag1 = tag.replace("__aarch64", "")
            else:
                return web.Response()

            images = self.parse_tag(repo, tag)

            for img in images:
                r1 = img.revision
                if not r1:
                    r1 = "N/A"

                r2 = img.app_revision
                if not r2:
                    r2 = "N/A"

                if img.travis_url:
                    desc = "Built from [Travis-CI](%s)" % img.travis_url
                else:
                    desc = "Built from N/A"

                embed = Embed(description=desc, color=0x40afde)
                author_name = "Image %s:%s" % (repo, tag1)
                docker_icon = "https://www.docker.com/sites/default/files/d8/2019-07/Moby-logo.png"
                url = "https://hub.docker.com/layers/exchangeunion/{}/{}/images/{}".format(repo, tag1, img.manifest_digest.replace(":", "-"))
                embed.set_author(name=author_name, icon_url=docker_icon, url=url)
                embed.add_field(name="Platform", value=img.platform)

                if "__" in tag1:
                    branch = tag1.split("__")[1]
                else:
                    branch = "master"

                embed.add_field(name="Branch", value=branch)
                embed.add_field(name="Size", value=humanize.naturalsize(img.size, binary=True))
                embed.add_field(name="Image Digest", value=img.digest.replace("sha256:", ""), inline=False)

                commit_url = f"https://github.com/ExchangeUnion/xud-docker/commit/{r1}"
                commit = "[%s](%s)" % (self.context.xud_docker.get_commit_message(r1), commit_url)
                embed.add_field(name="Xud-Docker Commit", value=commit, inline=False)

                if repo == "xud":
                    pass
                elif repo == "lndbtc":
                    pass

                if repo != "utils":
                    commit_url = f"https://github.com/ExchangeUnion/xud-docker/commit/{r1}"
                    commit = "[%s](%s)" % (self.context.xud_docker.get_commit_message(r1), commit_url)
                    embed.add_field(name="Application Revision", value=r2, inline=False)

                message = await self.context.discord_template.send(embed=embed)
        except:
            self.logger.debug("Failed to process dockerhub webhook")
        return web.Response()
