from __future__ import annotations

import json
from typing import TYPE_CHECKING
from urllib.parse import parse_qs

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
            msg = f"🏗️ Travis build #{number}: **{result.lower()}**"
            msg += f"\n**Link:** <https://travis-ci.org/github/ExchangeUnion/xud-docker/builds/{build_id}>"
            msg += f"\n**Branch:** {branch}"
            msg += f"\n**Commit:** `{commit}`"
            msg += f"\n**Message:** {commit_message}"
            msg += f"\n**Tests:** N/A"
            self.context.discord_template.publish_message(msg)
        return web.Response()
