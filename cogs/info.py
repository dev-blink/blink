import discord
from discord.ext import commands
import datetime
import blink
import psutil
import platform

class Info(commands.Cog,name="Info"):
    def __init__(self,bot):
        self.bot = bot
        self.colour = bot.colour

    @commands.command(name="prefix")
    async def prefix(self, ctx, *, member: discord.Member=None):
        """Shows the bot's prefix."""
        await ctx.send("The bot prefix is ';' you can also use 'b;' or a ping." )

    @commands.command(name="creator")
    async def creator(self, ctx, *, member: discord.Member=None):
        """Shows the bot's creator."""
        await ctx.send("aaix#0001 created this bot.")
    
    @commands.command(name="invite")
    async def invite(self, ctx, *, member: discord.Member=None):
        """Shows an invite for the server."""
        embed=discord.Embed(title="Click here.", url="https://top.gg/bot/692738917236998154", description="Invite the bot to your server",colour=self.colour)
        embed.set_author(name="Invite me!")
        embed.set_thumbnail(url=ctx.guild.me.avatar_url_as(static_format='png'))

        await ctx.send(embed=embed)
    
    @commands.command(name="support")
    async def support(self, ctx, *, member: discord.Member=None):
        """Shows an invite for the support server."""
        embed=discord.Embed(title="https://discord.gg/d23VBaR", url="https://discord.gg/d23VBaR", description="Just ask for help.",colour=self.colour)
        embed.set_author(name="Join the support server!")
        embed.set_thumbnail(url=ctx.guild.me.avatar_url_as(static_format='png'))

        await ctx.send(embed=embed)
    
    @commands.command(name="info")
    async def info(self,ctx):
        """Shows info about the bot"""
        owner = self.bot.get_user(171197717559771136)
        embed = discord.Embed(title=f"blink!",url="https://top.gg/bot/692738917236998154",description=f"Blink is a multipurpose bot designed by {owner.mention} ({owner.name}#{owner.discriminator})\n[Vote for us here!](https://top.gg/bot/692738917236998154) || [Click for support](https://discord.gg/pCVhrMF)",colour=self.colour)
        embed.add_field(name="To start:",value=";help for info on commands")
        embed.set_thumbnail(url=ctx.guild.me.avatar_url_as(static_format="png"))
        return await ctx.send(embed=embed)
        
    @commands.command(name="uptime")
    async def uptime(self,ctx):
        return await ctx.send(embed=discord.Embed(title="Bot uptime:",description=f"Bot has been online for: {blink.prettydelta((datetime.datetime.utcnow() - self.bot.boottime).total_seconds())}",colour=self.bot.colour))
    
    @commands.command(name="hardware",aliases=["system","sys"])
    async def sys_stats(self,ctx):
        embed = discord.Embed(title="System metrics",
        description=f"```CPU Usage: {psutil.cpu_percent()}%\nMemory Usage: {psutil.virtual_memory().used >> 20}/{psutil.virtual_memory().total >> 20}MB\nFree disk space: {psutil.disk_usage('/').free >> 30}GB\n{psutil.cpu_count()} CPUs running {platform.platform()}```",colour=self.bot.colour)
        return await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Info(bot))
