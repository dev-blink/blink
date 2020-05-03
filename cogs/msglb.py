import discord
from discord.ext import commands


class MessageLB(commands.Cog,name="Message Leaderboard"):
    def __init__(self,bot):
        self.bot=bot

    @commands.Cog.listener("on_message")
    async def update_db(self,message):
        if message.author.bot or not message.guild:
            return
        result=await self.bot.DB.fetchrow(f"SELECT * FROM globalmsg WHERE id=$1",message.author.id)
        if not result:
            await self.bot.DB.execute(f"INSERT INTO globalmsg VALUES ($1,$2)",message.author.id,1)
        else:
            await self.bot.DB.execute(f"UPDATE globalmsg SET messages=$1 WHERE id=$2",result["messages"] + 1,message.author.id)
        return

    @commands.command(name="messages",aliases=["msgs"])
    async def view_messages(self,ctx,member:discord.Member=None):
        if not member:
            member=ctx.author
        count=await self.bot.DB.fetchrow(f"SELECT * FROM globalmsg WHERE id=$1",member.id)
        if not count:
            return await ctx.send("Nothing in our database.")
        embed=discord.Embed(description=f'{count["messages"]} messages sent.',colour=self.bot.colour)
        embed.set_author(name=f"{member}",icon_url=member.avatar_url_as(static_format="png"))
        return await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(MessageLB(bot))
