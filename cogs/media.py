import discord
from discord.ext import commands
import blink


class FetchMedia(commands.Cog,name="Media"):
    def __init__(self,bot):
        self.bot = bot
        self.colour = self.bot.colour
    

    @commands.command(name="enlarge")
    async def enlarge_emoji(self,ctx, emoji:discord.PartialEmoji=None):
        """Enlarges a custom emoji"""
        if not emoji:
            return await ctx.send("Please send an emoji.")
        embed = discord.Embed(description=f"**{emoji.name}**",colour=self.colour)
        embed.set_image(url=f"{emoji.url}?size=1024")
        return await ctx.send(embed=embed)



def setup(bot):
    bot.add_cog(FetchMedia(bot))