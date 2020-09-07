from __future__ import annotations

import json
import sys
import traceback
from typing import TYPE_CHECKING
from urllib.parse import parse_qs
import asyncio

from aiohttp import web
from discord import Embed

from .abc import Hook

if TYPE_CHECKING:
    pass


class TravisHook(Hook):
    async def _handle(self, payload: str):
        try:
            t = payload
            params = parse_qs(t)
            j = json.loads(params["payload"][0])
            repo = j["repository"]["name"]
            if repo == "xud-docker":
                build_id = j["id"]
                number = j["number"]
                result = j["result_message"]
                branch = j["branch"]
                commit = j["commit"]
                commit_message = j["message"]
                status = result.lower()
                if status == "passed":
                    status2 = f"**{status}** 🎉"
                else:
                    status2 = f"**{status}**"

                url = f"https://travis-ci.org/github/ExchangeUnion/xud-docker/builds/{build_id}"

                title = status2.capitalize()
                desc = "%s" % commit_message
                embed = Embed(title=title, description=desc, color=0xdec940)
                author_name = "Travis-CI 🏗️ Build #%s" % number
                travis_icon = "https://cdn.travis-ci.org/images/favicon-076a22660830dc325cc8ed70e7146a59.png"
                embed.set_author(name=author_name, url=url, icon_url=travis_icon)
                embed.add_field(name="Branch", value=branch)
                commit_url = f"https://github.com/ExchangeUnion/xud-docker/commit/{commit}"
                commit_message = self.get_commit_message(commit)
                embed.add_field(name="Commit", value="[%s](%s)" % (commit_message, commit_url))
                message = await self.discord.send(embed=embed)

                if status == "pending":
                    await message.add_reaction('🚫')
                elif status == "canceled" or status == "passed":
                    await message.add_reaction('🔄')
        except:
            title = "Internal Error"
            tb = traceback.format_exception(*sys.exc_info())
            desc = tb[-1]
            embed = Embed(title=title, description=desc, color=0xff0000)
            name = tb[0]
            tb = tb[1:-1]
            lines = []
            for line in tb:
                line = line.replace("  File", "File")
                line = line.replace("    ", "```python\n")
                line = line + "\n```"
                lines.append(line)
            embed.add_field(name=name, value="\n".join(lines))

            # for m in ctx.channel.members:
            #     if m.name == "bitdancer"
            # mention the bot author
            await self.discord.send(content="<@280196677988777986>", embed=embed)

    async def handle(self, request: web.Request) -> web.Response:
        payload = await request.text()
        asyncio.create_task(self._handle(payload))
        return web.Response()

    def get_commit_message(self, commit):
        return self.xud_docker.get_commit_message(commit)
