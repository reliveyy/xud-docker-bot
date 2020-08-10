from __future__ import annotations

from discord.ext.commands import command
import humanize

from .abc import BaseCog


class DockerhubCog(BaseCog, name="DockerHub Category"):
    @command()
    async def tags(self, ctx, repo: str):
        assert repo
        tags = self.context.dockerhub_client.get_tags(f"exchangeunion/{repo}")
        msg = "Repository **exchangeunion/{}** has **{}** tag(s) in total.".format(repo, len(tags))
        await ctx.send(msg)
        for t in tags:
            self.logger.debug("Iterating tag in %s repo: %r", repo, t)
            await ctx.send(f"• `{t.name}`  ~{humanize.naturalsize(t.size, binary=True)}")

    @command()
    async def cleanup(self, ctx, repo: str):
        assert repo
        tags = self.context.dockerhub_client.get_tags(f"exchangeunion/{repo}")
        remove_list = []
        for tag in tags:
            if "__" in tag:
                remove_list.append(tag)

    @command()
    async def remove(self, ctx, image: str):
        config = self.context.config.dockerhub
        client = self.context.dockerhub_client
        token = client.login(config.username, config.password)
        client.remove_tag(token, "exchangeunion/foo", "bar")
        client.logout(token)
        assert image

