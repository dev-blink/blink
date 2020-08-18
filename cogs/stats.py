import discord
from discord.ext import commands
import statcord
import secrets


class StatClient(statcord.Client):
    @property
    def servers(self):
        return self.bot.cluster.guilds

    @property
    def users(self):
        return self.bot.cluster.users


class Stats(commands.Cog,name="Stats"):
    def __init__(self,bot:commands.AutoShardedBot):
        self.bot=bot
        self.bot._cogs.stats = self
        if bot.beta:
            return
        self.statcord = StatClient(bot,secrets.statcord,custom1=self.logging,custom2=self.music)
        self.bot.add_listener(self.statcord_push,"on_command")
        self.statcord.start_loop()

    @commands.command(name="stats")
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def stats(self,ctx):
        """Shows stats about the bot"""
        embed=discord.Embed(title="Bot statistics!",colour=self.bot.colour,description=f"```Servers: {self.bot.cluster.guilds}\nUnique users: {self.bot.cluster.users}```")
        return await ctx.send(embed=embed)

    @commands.Cog.listener("on_guild_join")
    async def guild_join(self,guild):
        embed=discord.Embed(title=f"Bot added to guild {guild.id} on cluster {self.bot.cluster.name}",colour=0x00ff3c,description=f"Total guilds: {self.bot.cluster.guilds+1}")
        embed.add_field(name="Guild name:",value=f"{guild.name}")
        embed.add_field(name="Guild members:",value=f"{guild.member_count}")
        embed.add_field(name="Guild owner:",value=f"{guild.owner}\n{guild.owner.mention}")
        embed.set_thumbnail(url=guild.icon_url_as(static_format="png"))
        await self.bot.cluster.log_guilds(embed=embed)

    @commands.Cog.listener("on_guild_remove")
    async def guild_remove(self,guild):
        embed=discord.Embed(title=f"Bot removed from guild {guild.id} on cluster {self.bot.cluster.name}",colour=0xff0003,description=f"Total guilds: {self.bot.cluster.guilds-1}")
        embed.add_field(name="Guild name:",value=f"{guild.name}")
        embed.add_field(name="Guild members:",value=f"{guild.member_count}")
        embed.add_field(name="Guild owner:",value=f"{guild.owner}\n{guild.owner.mention}")
        embed.set_thumbnail(url=guild.icon_url_as(static_format="png"))
        await self.bot.cluster.log_guilds(embed=embed)

    async def statcord_push(self,ctx):
        self.statcord.command_run(ctx)

    async def logging(self):
        try:
            actions = str(self.bot.logActions)
        except AttributeError:
            actions = "0"
        self.bot.logActions = 0
        return actions

    async def music(self):
        music = self.bot.cluster.music
        if music == -1:
            return "0"
        else:
            return str(music)


def setup(bot):
    bot.add_cog(Stats(bot))
