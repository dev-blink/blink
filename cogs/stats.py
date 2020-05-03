import discord
from discord.ext import commands
import blink


class Stats(commands.Cog,name="Stats"):
    def __init__(self,bot):
        self.bot=bot
        self.statsserver=bot.statsserver
        self.newguilds=self.statsserver.get_channel(blink.Config.newguilds())

    @commands.command(name="stats")
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def stats(self,ctx):
        """Shows stats about the bot"""
        embed=discord.Embed(title="Bot statistics!",colour=self.bot.colour,description=f"```Servers: {len(self.bot.guilds)}\nUnique users: {len(self.bot.users) - 1}```\n[Vote for us here!](https://top.gg/bot/692738917236998154)")
        return await ctx.send(embed=embed)

    @commands.Cog.listener("on_guild_join")
    async def guild_join(self,guild):
        embed=discord.Embed(title=f"Bot added to guild {guild.id}",colour=0x00ff3c,description=f"Total guilds: {len(self.bot.guilds)}")
        embed.add_field(name="Guild name:",value=f"{guild.name}")
        embed.add_field(name="Guild members:",value=f"{guild.member_count}")
        embed.add_field(name="Guild owner:",value=f"{guild.owner.name}#{guild.owner.discriminator}\n{guild.owner.mention}")
        embed.set_thumbnail(url=guild.icon_url_as(static_format="png"))
        await self.newguilds.send(embed=embed)

    @commands.Cog.listener("on_guild_remove")
    async def guild_remove(self,guild):
        embed=discord.Embed(title=f"Bot removed from guild {guild.id}",colour=0xff0003,description=f"Total guilds: {len(self.bot.guilds)}")
        embed.add_field(name="Guild name:",value=f"{guild.name}")
        embed.add_field(name="Guild members:",value=f"{guild.member_count}")
        embed.add_field(name="Guild owner:",value=f"{guild.owner.name}#{guild.owner.discriminator}\n{guild.owner.mention}")
        embed.set_thumbnail(url=guild.icon_url_as(static_format="png"))
        await self.newguilds.send(embed=embed)


def setup(bot):
    bot.add_cog(Stats(bot))
