import dbl
from discord.ext import commands
import blink


class TopGG(commands.Cog):
    """Handles interactions with the top.gg API"""

    def __init__(self, bot):
        self.bot=bot
        self.token=blink.Config.DBLtoken()
        self.dblpy=dbl.DBLClient(self.bot, self.token, autopost=True)  # Autopost will post your guild count every 30 minutes

    async def on_guild_post(self):
        await self.dbllog.send(f"Posted {len(self.bot.guilds)} guilds to DBL.")


def setup(bot):
    bot.add_cog(TopGG(bot))
