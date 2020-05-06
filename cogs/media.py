import discord
from discord.ext import commands
import aiohttp
import box
import random
import asyncio


class Media(commands.Cog,name="Media"):
    def __init__(self,bot):
        self.bot=bot
        self.colour=self.bot.colour
        self.session=aiohttp.ClientSession()

    def __unload(self):
        asyncio.create_task(self.session.close())

    @commands.command(name="enlarge")
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def enlarge_emoji(self,ctx, emoji:discord.PartialEmoji=None):
        """Enlarges a custom emoji"""
        if not emoji:
            return await ctx.send("Please send an emoji.")
        embed=discord.Embed(description=f"**{emoji.name}**",colour=self.colour)
        embed.set_image(url=f"{emoji.url}?size=1024")
        return await ctx.send(embed=embed)

    @commands.command(name="screenshot",aliases=["ss"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def ss(self, ctx, *, url: str):
        async with ctx.typing():
            try:
                screener = "http://magmachain.herokuapp.com/api/v1"
                async with self.session.post(screener, headers=dict(website=url)) as r:
                    website = (await r.json())["snapshot"]
                    await ctx.send(embed=discord.Embed(color=self.bot.colour).set_image(url=website))
            except Exception:
                return await ctx.send("An error occured. most likely due to the unstable nature of the api.")

    @commands.command(name="meme",aliases=["memes"])
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    @commands.cooldown(1,3,commands.BucketType.member)
    async def r_memes(self,ctx):
        """Gets a meme from r/memes"""
        r=await self.session.get("https://reddit.com/r/memes.json")
        r=await r.json()
        r=box.Box(r)
        data=random.choice(r.data.children).data
        embed=discord.Embed(title=data.title,url=data.url,colour=self.bot.colour)
        embed.set_image(url=data.url)
        return await ctx.send(embed=embed)

    @commands.command(name="dankmeme",aliases=["dankmemes"])
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    @commands.cooldown(1,3,commands.BucketType.member)
    async def r_dankmemes(self,ctx):
        """Gets a meme from r/dankmemes"""
        r=await self.session.get("https://reddit.com/r/dankmemes.json")
        r=await r.json()
        r=box.Box(r)
        data=random.choice(r.data.children).data
        embed=discord.Embed(title=data.title,url=data.url,colour=self.bot.colour)
        embed.set_image(url=data.url)
        return await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Media(bot))
