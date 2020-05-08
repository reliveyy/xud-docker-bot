from discord.ext import commands
from requests import get
from collections import namedtuple
import humanize
import logging

logger = logging.getLogger(__name__)

bot = commands.Bot(command_prefix='.')

@bot.event
async def on_ready():
    logger.info('%s has connected to Discord!', bot.user)


class DockerHubCategory(commands.Cog, name="DockerHub Category"):
    @commands.command()
    async def tags(self, ctx, name):
        tags = []
        Tag = namedtuple("Tag", ["name", "size"])
        url = f"https://hub.docker.com/v2/repositories/exchangeunion/{name}/tags"
        while True:
            j = get(url).json()
            url = j["next"]
            if not url:
                break
            for item in j["results"]:
                tags.append(Tag(item["name"], item["full_size"]))

        await ctx.send("Repository **exchangeunion/{}** has **{}** tag(s) in total.".format(name, len(tags)))

        for t in tags:
            print(t)
            await ctx.send(f"• `{t.name}`  ~{humanize.naturalsize(t.size, binary=True)}")


bot.add_cog(DockerHubCategory())
