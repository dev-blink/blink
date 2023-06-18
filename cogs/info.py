# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


import discord
from discord.ext import commands
import datetime
import blink
import psutil
import platform
import time


class Info(blink.Cog, name="Info"):
    @commands.command(name="invite")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def invite(self, ctx):
        """A bot invite"""
        embed = discord.Embed(
            title="Click here.",
            url=f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&scope=bot+applications.commands&permissions=8",
            description="Invite the bot to your server", colour=self.bot.colour
        )
        embed.set_author(name="Invite me!")
        embed.set_thumbnail(
            url=self.bot.user.display_avatar.replace(static_format='png')
        )

        await ctx.send(embed=embed)

    @commands.command(name="support")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def support(self, ctx):
        """Shows an invite for the support server."""
        embed = discord.Embed(
            title="https://discord.gg/d23VBaR",
            url="https://discord.gg/d23VBaR",
            description="Just ask for help.",
            colour=self.bot.colour
        )
        embed.set_author(name="Join the support server!")
        embed.set_thumbnail(
            url=self.bot.user.display_avatar.replace(static_format='png')
        )

        await ctx.send(embed=embed)

    @commands.command(name="info", aliases=["about"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def info(self, ctx):
        """Shows info about the bot"""
        embed = discord.Embed(
            title="blink!", url="https://blinkbot.me",
            description="Blink is a multipurpose bot designed for simplicity\n [Click for support](https://discord.gg/pCVhrMF) | [Privacy Policy](https://www.blinkbot.me/policy.html) | [Invite](https://discord.com/oauth2/authorize?client_id=692738917236998154&scope=bot+applications.commands&permissions=8)",
            colour=self.bot.colour
        )
        embed.add_field(name="To start:", value=";help for info on commands")
        embed.set_thumbnail(
            url=self.bot.user.display_avatar.replace(static_format='png')
        )
        return await ctx.send(embed=embed)

    @commands.command(name="uptime")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def uptime(self, ctx):
        """Bots uptime"""
        return await ctx.send(embed=discord.Embed(title="Bot uptime:", description=f"Cluster {self.bot.cluster.identifier} has been online for: {blink.prettydelta((discord.utils.utcnow() - self.bot.boottime).total_seconds())}", colour=self.bot.colour))

    @commands.command(name="hardware", aliases=["system", "sys"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def sys_stats(self, ctx):
        """System Stats"""
        embed = discord.Embed(
            title="System metrics",
            description=f"```CPU Usage: {psutil.cpu_percent()}%\nMemory Usage: {psutil.virtual_memory().used >> 20}/{psutil.virtual_memory().total >> 20}MB\nFree disk space: {psutil.disk_usage('/').free >> 30}GB\n{psutil.cpu_count()} CPUs running {platform.platform()}```",
            colour=self.bot.colour
        )
        return await ctx.send(embed=embed)

    @commands.command(name="ping")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def ping(self, ctx):
        """Pong..."""
        before = time.monotonic() # rtt time to send a message
        message = await ctx.send("pong")
        ping = (time.monotonic() - before) * 1000 # in ms
        await message.edit(embed=discord.Embed(
            title="\U0001f3d3 Pong",
            description=f"HTTP request time: {int(ping)}ms\nWebsocket latency: {round((self.bot.latency * 1000))}ms\nCluster latency: {self.bot.cluster.latency}ms\nDB cacherate: {self.bot.cacherate()}%\nSongs cached: {len(self.bot._cogs.member.lyric_cache)}-{len(self.bot._cogs.member.dead_tracks)}",
            colour=self.bot.colour
        ), content=None)


async def setup(bot):
    await bot.add_cog(Info(bot, "info"))
