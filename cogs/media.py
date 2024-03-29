# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <blink@aaix.dev>, 29 Dec 2023


import discord
from discord.ext import commands
import aiohttp
import box
import random
import blink


class Media(blink.Cog, name="Media"):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = aiohttp.ClientSession()

    async def _do_reddit(self, term):
        """Fetch and format a random image from a subreddit"""
        async with self.session.get(f"https://reddit.com/r/{term}.json") as resp:
            r = await resp.json()
        try:
            r["error"]
        except KeyError:
            pass
        else:
            return discord.Embed(title=f"{r['error']} error...", colour=discord.Colour.red())
        r = box.Box(r) # box turns dict key into object like type() but recursively
        data = random.choice(r.data.children).data # random reddit post
        embed = discord.Embed(
            title=data.title,
            url=data.url,
            colour=self.bot.colour
        )
        embed.set_image(url=data.url)
        return embed

    @commands.command(name="enlarge")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def enlarge_emoji(self, ctx, emoji: discord.PartialEmoji):
        """Enlarges a custom emoji"""
        embed = discord.Embed(
            description=f"**{emoji.name}**",
            colour=self.bot.colour
        )
        embed.set_image(url=f"{emoji.url}?size=1024")
        return await ctx.send(embed=embed)

    # trash commands trash memes
    # some people use it why idk
    @commands.command(name="meme", aliases=["memes"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def r_memes(self, ctx):
        """Gets a meme from r/memes"""
        return await ctx.send(embed=await self._do_reddit("memes"))

    @commands.command(name="dankmeme", aliases=["dankmemes"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.cooldown(1, 3, commands.BucketType.member)
    async def r_dankmemes(self, ctx):
        """Get a meme from r/dankmemes"""
        return await ctx.send(embed=await self._do_reddit("dankmemes"))


async def setup(bot):
    await bot.add_cog(Media(bot, "media"))
