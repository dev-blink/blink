import discord
from discord.ext import commands
import aiohttp
import random
import box
import asyncio


class NSFW(commands.Cog,name="NSFW"):
    def __init__(self,bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.bot.add_cog(self)

    def __unload(self):
        asyncio.create_task(self.session.close())

    async def _do_reddit(self,term):
        r=await self.session.get(f"https://reddit.com/r/{term}.json")
        r=await r.json()
        try:
            r["error"]
        except KeyError:
            pass
        else:
            return discord.Embed(title=f"{r['error']} error...",colour=discord.Colour.red())
        r=box.Box(r)
        data=random.choice(r.data.children).data
        embed=discord.Embed(title=data.title,url=data.url,colour=self.bot.colour)
        embed.set_image(url=data.url)
        return embed

    @commands.group(name="nsfw",invoke_without_command=True)
    @commands.is_nsfw()
    async def nsfw(self,ctx):
        """Nsfw commands"""
        return await ctx.send(embed=discord.Embed(title="NSFW Commands",colour=self.bot.colour,description="\n".join(list((f"**{c.name}** {c.help}" for c in ctx.command.commands)))))

    @nsfw.command(name="belle",aliases=["belledeplhine","delphine"])
    @commands.is_nsfw()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    @commands.cooldown(1,3,commands.BucketType.member)
    async def belle_delphine(self,ctx):
        """Random picture of belle delphine"""
        return await ctx.send(embed=discord.Embed(colour=self.bot.colour).set_image(url=f"https://hentai.izthe.best/v1/random?{random.random()}"))

    @nsfw.command(name="hentai")
    @commands.is_nsfw()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    @commands.cooldown(1,3,commands.BucketType.member)
    async def r_hentai(self,ctx):
        """Random hentai (reddit)"""
        return await ctx.send(embed=await self._do_reddit("hentai"))

    @nsfw.command(name="porn")
    @commands.is_nsfw()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    @commands.cooldown(1,3,commands.BucketType.member)
    async def r_porn(self,ctx):
        """Random porn (reddit)"""
        return await ctx.send(embed=await self._do_reddit("porn"))

    @nsfw.command(name="ass")
    @commands.is_nsfw()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    @commands.cooldown(1,3,commands.BucketType.member)
    async def r_ass(self,ctx):
        """Random ass (reddit)"""
        return await ctx.send(embed=await self._do_reddit("ass"))

    @nsfw.command(name="bondage")
    @commands.is_nsfw()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    @commands.cooldown(1,3,commands.BucketType.member)
    async def r_bondage(self,ctx):
        """Random bondage (reddit)"""
        return await ctx.send(embed=await self._do_reddit("bondage"))

    @nsfw.command(name="thicc")
    @commands.is_nsfw()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    @commands.cooldown(1,3,commands.BucketType.member)
    async def r_thicc(self,ctx):
        """Random thicc (reddit)"""
        return await ctx.send(embed=await self._do_reddit("thicc"))

    @nsfw.command(name="petite")
    @commands.is_nsfw()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    @commands.cooldown(1,3,commands.BucketType.member)
    async def r_petitie(self,ctx):
        """Random petitie (reddit)"""
        return await ctx.send(embed=await self._do_reddit("petite"))


def setup(bot):
    NSFW(bot)
