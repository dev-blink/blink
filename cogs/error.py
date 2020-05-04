import traceback
import sys
from discord.ext import commands, menus
import discord
import blink
import datetime
import asyncpg


class CommandErrorHandler(commands.Cog,name="ErrorHandler"):
    def __init__(self, bot):
        self.bot=bot
        self.statsserver=bot.statsserver
        self.errorreport=self.statsserver.get_channel(blink.Config.errors())

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command.
        ctx   : Context
        error : Exception"""

        ignored=(commands.CommandNotFound)
        error=getattr(error, 'original', error)

        if isinstance(error, ignored):
            return

        elif isinstance(error,commands.MissingRequiredArgument):
            return await ctx.send(error)

        elif isinstance(error,commands.TooManyArguments):
            return await ctx.send("Too many arguments passed...")

        elif isinstance(error,menus.CannotAddReactions):
            return await ctx.send("I am unable to initialize the reaction menu. Please give me permissions to add reactions.")

        elif isinstance(error,commands.BotMissingPermissions):
            return await ctx.send(f"***ERROR*** :{error}")
        elif isinstance(error, commands.DisabledCommand):
            return await ctx.send(f'**`{ctx.command}`** has been disabled.')

        elif isinstance(error, commands.MissingPermissions):
            return await ctx.send(f'You do not have permission to use the command **`{ctx.command}`**')

        elif isinstance(error, commands.NotOwner):
            try:
                return await ctx.message.add_reaction("\U000026d4")
            except discord.Forbidden:
                pass

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.author.send(f'**`{ctx.command}`** can not be used in Private Messages.')
            except discord.Forbidden:
                pass
        elif isinstance(error, discord.errors.Forbidden):
            return await ctx.send("I do not have permission to do that.")

        elif isinstance(error, commands.BadArgument):
            return await ctx.send(error)

        elif isinstance(error, commands.CommandOnCooldown):
            if ctx.author.id in self.bot.owner_ids:
                await ctx.reinvoke()
                return
            try:
                return await ctx.message.add_reaction("\U000023f2")
            except discord.Forbidden:
                pass
        elif isinstance(error, blink.IncorrectChannelError):
            return

        elif isinstance(error, blink.NoChannelProvided):
            return await ctx.send('You must be in a voice channel or provide one to connect to.')
        elif isinstance(error,commands.NSFWChannelRequired):
            return await ctx.send("I am unable to display NSFW images in this channel")

        elif isinstance(error,commands.MaxConcurrencyReached):
            return await ctx.send(error)

        elif isinstance(error,asyncpg.exceptions.PostgresError):
            return await ctx.send(error)

        await ctx.send(embed=discord.Embed(title="Uh Oh! Something went wrong...",description="if this persists please contact the bot dev via ;support\nThis incident has been logged.",colour=discord.Colour.red()))
        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        if "beta" not in self.bot.user.name:
            await self.errorreport.send(f"Error occureed in guild: {ctx.guild} | {ctx.guild.id} channel: {ctx.channel.mention} | {ctx.channel.id} \nCommand: **`{ctx.message.content}`** " + "```" + str("\n".join(traceback.format_exception(type(error), error, error.__traceback__))) + f"```\nOCCURED AT : {datetime.datetime.utcnow().isoformat()}")


def setup(bot):
    bot.add_cog(CommandErrorHandler(bot))