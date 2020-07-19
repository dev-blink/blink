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
            "dlabs":secrets.dlabsapi
        }
        self.loop.start()

    @tasks.loop(hours=1)
    async def loop(self):
        await self.post()

    async def post(self):
        guilds = len(self.bot.guilds)
        async with aiohttp.ClientSession() as cs:
            r = await cs.post("https://top.gg/api/bots/692738917236998154/stats",data={"server_count":guilds},headers={"Authorization":self.tokens["dbl"]})
            if not r.status == 200:
                await self.bot.warn(f"Error in DBL post, response {r.status} `{await r.json()}`",False)

        async with aiohttp.ClientSession() as cs:
            r = await cs.post("https://api.botsdatabase.com/v1/bots/692738917236998154",json={"servers":guilds},headers={"Authorization":self.tokens["bdb"],"Content-Type":"application/json"})
            if not r.status == 200:
                await self.bot.warn(f"Error in BDB post, response {r.status} `{await r.json()}`",False)

        async with aiohttp.ClientSession() as cs:
            r = await cs.post("https://api.discordextremelist.xyz/v2/bot/692738917236998154/stats",json={"guildCount":guilds},headers={"Authorization":self.tokens["del"],"Content-Type":"application/json"})
            if not r.status == 200:
                await self.bot.warn(f"Error in DEL post, response {r.status} `{await r.json()}`",False)

        async with aiohttp.ClientSession() as cs:
            r = await cs.post("https://bots.discordlabs.org/v2/bot/692738917236998154/stats",json={"server_count":guilds,"token":self.tokens["dlabs"]})
            if not r.status == 200:
                await self.bot.warn(f"Error in DLABS post, response {r.status} `{await r.json()}`",False)


def setup(bot):
    bot.add_cog(ListingHandler(bot))
