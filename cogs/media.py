import discord
from discord.ext import commands
import blink
import aiohttp
import box
import random
class Media(commands.Cog,name="Media"):
    def __init__(self,bot):
        self.bot = bot
        self.colour = self.bot.colour
    

    @commands.command(name="enlarge")
    async def enlarge_emoji(self,ctx, emoji:discord.PartialEmoji=None):
        """Enlarges a custom emoji"""
        if not emoji:
            return await ctx.send("Please send an emoji.")
        embed = discord.Embed(description=f"**{emoji.name}**",colour=self.colour)
        embed.set_image(url=f"{emoji.url}?size=1024")
        return await ctx.send(embed=embed)


    @commands.command(name="meme",aliases=["memes"])
    @commands.cooldown(1,3,commands.BucketType.member)
    async def r_memes(self,ctx):
        """Gets a meme from r/memes"""
        session = aiohttp.ClientSession()
        r = await session.get("https://reddit.com/r/memes.json")
        r = await r.json()
        r = box.Box(r)
        data = random.choice(r.data.children).data
        print(f"DATA{data}")
        embed = discord.Embed(title=data.title,url=data.url,colour=self.bot.colour)
        embed.set_image(url=data.url)
        await session.close()
        return await ctx.send(embed=embed)
    
    @commands.command(name="dankmeme",aliases=["dankmemes"])
    @commands.cooldown(1,3,commands.BucketType.member)
    async def r_dankmemes(self,ctx):
        """Gets a meme from r/dankmemes"""
        session = aiohttp.ClientSession()
        r = await session.get("https://reddit.com/r/dankmemes.json")
        r = await r.json()
        r = box.Box(r)
        data = random.choice(r.data.children).data
        print(f"DATA{data}")
        embed = discord.Embed(title=data.title,url=data.url,colour=self.bot.colour)
        embed.set_image(url=data.url)
        await session.close()
        return await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Media(bot))