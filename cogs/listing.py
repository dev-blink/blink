import discord
from discord.ext import tasks
import secrets
import aiohttp
import blink


class ListingHandler(blink.Cog):
    """Handles interactions with bot listing sites """

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
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
            r = await cs.post("https://api.botsdatabase.com/v1/bots/692738917236998154",json={"servers":guilds},headers={"Authorization":self.tokens["bdb"],"Content-Type":"application/json"})
            if not r.status == 200:
                await self.bot.warn(f"Error in BDB post, response {r.status}",False)
            await cs.close()

        async with aiohttp.ClientSession() as cs:
            r = await cs.post("https://api.discordextremelist.xyz/v2/bot/692738917236998154/stats",json={"guildCount":guilds},headers={"Authorization":self.tokens["del"],"Content-Type":"application/json"})
            if not r.status == 200:
                await self.bot.warn(f"Error in DEL post, response {r.status} ",False)
                with open("del.html") as f:
                    f.write(str(discord.http.json_or_text(r)))
            await cs.close()


def setup(bot):
    if bot.beta:
        return
    bot.add_cog(ListingHandler(bot,"listing"))
