from discord.ext import commands,tasks
import secrets
import aiohttp


class ListingHandler(commands.Cog):
    """Handles interactions with bot listing sites """

    def __init__(self, bot):
        self.bot=bot
        self.tokens={
            "dbl":secrets.dblapi,
            "bdb":secrets.bdbapi,
            "del":secrets.delapi,
        }
        self.loop.start()

    @tasks.loop(hours=1)
    async def loop(self):
        try:
            await self.post()
        except Exception as e:
            await self.bot.warn(f"Error in guild post {type(e)} {e}",False)

    async def post(self):
        guilds = self.bot.cluster.guilds
        async with aiohttp.ClientSession() as cs:
            r = await cs.post("https://top.gg/api/bots/692738917236998154/stats",data={"server_count":guilds},headers={"Authorization":self.tokens["dbl"]})
            if not r.status == 200:
                await self.bot.warn(f"Error in DBL post, response {r.status} `{await r.json()}`",False)
            await cs.close()

        async with aiohttp.ClientSession() as cs:
            r = await cs.post("https://api.botsdatabase.com/v1/bots/692738917236998154",json={"servers":guilds},headers={"Authorization":self.tokens["bdb"],"Content-Type":"application/json"})
            if not r.status == 200:
                await self.bot.warn(f"Error in BDB post, response {r.status} `{await r.json()}`",False)
            await cs.close()

        async with aiohttp.ClientSession() as cs:
            r = await cs.post("https://api.discordextremelist.xyz/v2/bot/692738917236998154/stats",json={"guildCount":guilds},headers={"Authorization":self.tokens["del"],"Content-Type":"application/json"})
            if not r.status == 200:
                await self.bot.warn(f"Error in DEL post, response {r.status} `{await r.json()}`",False)
            await cs.close()


def setup(bot):
    if bot.beta:
        return
    bot.add_cog(ListingHandler(bot))
