from discord.ext import commands,tasks
import secrets
import aiohttp


class ListingHandler(commands.Cog):
    """Handles interactions with bot listing sites """

    def __init__(self, bot):
        self.bot=bot
        self.tokens={
            "dbl":secrets.dbl,
            "bdb":secrets.bdb,
        }
        self.loop.start()

    @tasks.loop(hours=1)
    async def loop(self):
        await self.post()

    async def post(self):
        async with aiohttp.ClientSession() as cs:
            r = await cs.post("https://top.gg/api/bots/692738917236998154/stats",data={"server_count":len(self.bot.guilds)},headers={"Authorization":self.tokens["dbl"]})
            if not r.status == 200:
                await self.bot.warn(f"Error in DBL post response {r.status} `{await r.json()}`",False)

        async with aiohttp.ClientSession() as cs:
            r = await cs.post("https://api.botsdatabase.com/v1/bots/692738917236998154",json={"servers":(len(self.bot.guilds))},headers={"Authorization":self.tokens["bdb"],"Content-Type":"application/json"})
            if not r.status == 200:
                await self.bot.warn(f"Error in BDB post response {r.status} `{await r.json()}`",False)


def setup(bot):
    bot.add_cog(ListingHandler(bot))
