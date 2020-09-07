from __future__ import annotations

import traceback

from discord import Embed
from discord.ext.commands import Cog, Context, CommandError, CommandNotFound


class BaseCog(Cog):
    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError):
        title = "Internal Error"
        if not error.__cause__:
            if isinstance(error, CommandNotFound):
                embed = Embed(title="Command Not Found", description=str(error), color=0xff0000)
                await ctx.send(embed=embed)
                return
        else:
            error = error.__cause__

        tb = traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__)
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
        embed.set_footer(text="◇ xud-docker-bot | v1.0.0.dev57")

        # @bitdancer (Yang Yang)
        await ctx.send(content="<@280196677988777986>", embed=embed)
