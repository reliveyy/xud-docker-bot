from __future__ import annotations

import json
from typing import TYPE_CHECKING
from urllib.parse import parse_qs
from discord.ext.commands import Cog
import re

from aiohttp import web
from .abc import Hook

if TYPE_CHECKING:
    pass


class TravisHook(Hook):
    async def handle(self, request: web.Request) -> web.Response:
        t = await request.text()
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
            msg = f"🏗️ Travis build #{number}: {status2}"
            msg += f"\n**Link:** <https://travis-ci.org/github/ExchangeUnion/xud-docker/builds/{build_id}>"
            msg += f"\n**Branch:** {branch}"
            msg += f"\n**Commit:** `{commit}`"
            msg += f"\n**Message:** {commit_message}"
            message = await self.context.discord_template.publish_message_async(msg)
            if status == "pending":
                await message.add_reaction('🚫')
            elif status == "canceled" or status == "passed":
                await message.add_reaction('🔄')
        return web.Response()

