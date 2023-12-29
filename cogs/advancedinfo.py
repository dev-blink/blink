# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <blink@aaix.dev>, 29 Dec 2023


import re
import aiohttp
import discord
from discord.ext import commands
import base64
import blink


class AdvancedInfo(blink.Cog, name="Advanced info"):
    """More technical information commands"""
    @commands.command(name="token", aliases=["guesstoken"])
    @commands.guild_only()
    async def tokenguess(self, ctx, member: discord.Member = None):
        """Guesses a users token, with a hint of accuracy"""
        if not member:
            member = ctx.author
        # token is b64 encoded user id
        # + b64 timestamp generated#
        # + cryptographic hash
        p1 = base64.b64encode(str(member.id).encode("UTF-8"))
        p1 = p1.decode("UTF-8") # bytes to string
        p2 = "#" * 6
        p3 = "#" * 27
        out = f"Non mfa token: **`{p1}.{p2}.{p3}`**"
        return await ctx.send(out)

    @commands.command(name="lookup")
    @commands.bot_has_permissions(embed_links=True, send_messages=True)
    async def lookup_user(self, ctx, userid: int):
        """Looks up a user by their ID"""
        try:
            user = await self.bot.fetch_user(userid)
        except Exception:
            return await ctx.send("I am unable to find that user.")

        embed = discord.Embed(
            title=f"User lookup for: {userid}",
            description=user.mention,
            colour=self.bot.colour
        )
        registered = user.created_at

        embed.add_field(name="Tag:", value=f"{user}")
        registerdate = str(registered.day) + "/" + str(registered.month) + "/" + str(
            registered.year) + "  " + str(registered.hour) + ":" + str(registered.minute).zfill(2)

        embed.add_field(name="User registered:",
                        value=registerdate, inline=True)
        return await ctx.send(embed=embed)

    @commands.command(name="checktoken", aliases=["tokencheck"], hidden=True)
    @commands.bot_has_permissions(embed_links=True, send_messages=True)
    @commands.is_owner()
    async def token_eval(self, ctx, token):
        """Check a bot token."""
        # token regex
        if not re.compile(r"([a-zA-Z0-9]{24}\.[a-zA-Z0-9]{6}\.[a-zA-Z0-9_\-]{27}|mfa\.[a-zA-Z0-9_\-]{84})").match(token):
            return await ctx.send("Invalid token.")

        # try user first
        # then try bot
        async with aiohttp.ClientSession() as cs:
            async with cs.get("https://discord.com/api/v9/users/@me", headers={"Authorization":token}) as req:
                if req.status == 401:
                    if token.startswith("mfa"):
                        return await ctx.send("Unknown Token")
                else:
                    return await ctx.send(await req.text())
            async with cs.get("https://discord.com/api/v9/users/@me", headers={"Authorization":f"Bot {token}"}) as req:
                if req.status == 401:
                    return await ctx.send("Unknown Token")
                else:
                    return await ctx.send(await req.text())


async def setup(bot):
    await bot.add_cog(AdvancedInfo(bot, "advancedinfo"))
