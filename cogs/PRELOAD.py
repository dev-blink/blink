from discord.ext import commands


class PRELOAD(commands.Cog):
    def __init__(self,bot):
        self.bot=bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        return await ctx.send("Bot is still starting...\n***read its status maybe?***")


def setup(bot):
    bot.add_cog(PRELOAD(bot))
