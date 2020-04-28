import traceback
import sys
from discord.ext import commands
import discord
import blink
import datetime

class CommandErrorHandler(commands.Cog,name="ErrorHandler"):
    def __init__(self, bot):
        self.bot = bot
        self.statsserver = bot.statsserver
        self.errorreport = self.statsserver.get_channel(blink.Config.errors())
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command.
        ctx   : Context
        error : Exception"""


        ignored = (commands.CommandNotFound, commands.UserInputError)
        error = getattr(error, 'original', error)

        
        if isinstance(error, ignored):
            return

        elif isinstance(error, commands.DisabledCommand):
            return await ctx.send(f'**`{ctx.command}`** has been disabled.')
        
        elif isinstance(error, commands.MissingPermissions):
            return await ctx.send(f'you do not have permission to use the command **`{ctx.command}`**')

        elif isinstance(error, commands.NotOwner):
            return await ctx.message.add_reaction("\U000026d4")

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.author.send(f'**`{ctx.command}`** can not be used in Private Messages.')
            except:
                pass
        elif isinstance(error, discord.errors.Forbidden):
            return await ctx.send("I do not have permission to do that.")

        elif isinstance(error, commands.BadArgument):
            return await ctx.send('Somthing went wrong, (BadArgument)')

        elif isinstance(error, commands.CommandOnCooldown):
            if ctx.author.id in self.bot.owner_ids:
                await ctx.reinvoke()
                return
            return await ctx.message.add_reaction("\U000023f2")
            
        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        if not "beta" in self.bot.user.name:
            await self.errorreport.send(f"Error occureed in guild: {ctx.guild}\nCommand: **`{ctx.message.content}`** " + "```" + str("\n".join(traceback.format_exception(type(error), error, error.__traceback__)))+ f"```\nOCCURED AT : {datetime.datetime.utcnow().isoformat()}")

    
                

def setup(bot):
    bot.add_cog(CommandErrorHandler(bot))