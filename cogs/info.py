import discord
from discord.ext import commands
import datetime
import blink
import psutil
import platform
import time


class Info(blink.Cog,name="Info"):
    @commands.command(name="prefix")
    @commands.bot_has_permissions(send_messages=True)
    async def prefix(self, ctx):
        """Shows the bot's prefix."""
        await ctx.send("The bot prefix is ';' you can also use 'b;' or a ping.")

    @commands.command(name="creator")
    @commands.bot_has_permissions(send_messages=True)
    async def creator(self, ctx):
        """Shows the bot's creator."""
        await ctx.send("aaix#0001 created this bot.")

    @commands.command(name="invite")
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def invite(self, ctx):
        """A bot invite"""
        embed=discord.Embed(title="Click here.", url="https://blinkbot.me", description="Invite the bot to your server",colour=self.bot.colour)
        embed.set_author(name="Invite me!")
        embed.set_thumbnail(url=self.bot.user.avatar_url_as(static_format='png'))

        await ctx.send(embed=embed)

    @commands.command(name="support")
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def support(self, ctx):
        """Shows an invite for the support server."""
        embed=discord.Embed(title="https://discord.gg/d23VBaR", url="https://discord.gg/d23VBaR", description="Just ask for help.",colour=self.bot.colour)
        embed.set_author(name="Join the support server!")
        embed.set_thumbnail(url=ctx.guild.me.avatar_url_as(static_format='png'))

        await ctx.send(embed=embed)

    @commands.command(name="info",aliases=["about"])
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def info(self,ctx):
        """Shows info about the bot"""
        owner=self.bot.get_user(171197717559771136)
        embed=discord.Embed(title="blink!",url="https://blinkbot.me",description=f"Blink is a multipurpose bot designed by {owner.mention} ({owner.name}#{owner.discriminator})\n [Click for support](https://discord.gg/pCVhrMF) | [Privacy Policy](https://cdn.blinkbot.me/policy)",colour=self.bot.colour)
        embed.add_field(name="To start:",value=";help for info on commands")
        embed.set_thumbnail(url=ctx.guild.me.avatar_url_as(static_format="png"))
        return await ctx.send(embed=embed)

    @commands.command(name="uptime")
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def uptime(self,ctx):
        """Bots uptime"""
        return await ctx.send(embed=discord.Embed(title="Bot uptime:",description=f"Cluster {self.bot.cluster.name} has been online for: {blink.prettydelta((datetime.datetime.utcnow() - self.bot.boottime).total_seconds())}",colour=self.bot.colour))

    @commands.command(name="hardware",aliases=["system","sys"])
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def sys_stats(self,ctx):
        """System Stats"""
        embed=discord.Embed(title="System metrics",description=f"```CPU Usage: {psutil.cpu_percent()}%\nMemory Usage: {psutil.virtual_memory().used >> 20}/{psutil.virtual_memory().total >> 20}MB\nFree disk space: {psutil.disk_usage('/').free >> 30}GB\n{psutil.cpu_count()} CPUs running {platform.platform()}```",colour=self.bot.colour)
        return await ctx.send(embed=embed)

    @commands.command(name="ping")
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def ping(self,ctx):
        """Pong..."""
        before=time.monotonic()
        message=await ctx.send("pong")
        ping=(time.monotonic() - before) * 1000
        await message.edit(embed=discord.Embed(title="\U0001f3d3 Pong",description=f"Message ping: {int(ping)}ms\nWebsocket latency: {round((self.bot.latency * 1000),4)}ms",colour=self.bot.colour),content=None)


def setup(bot):
    bot.add_cog(Info(bot,"info"))
