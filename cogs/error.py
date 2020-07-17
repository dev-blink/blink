import traceback
from discord.ext import commands, menus
import discord
import blink
import datetime
import asyncpg
from wavelink import ZeroConnectedNodes as NoNodes


class CommandErrorHandler(commands.Cog,name="ErrorHandler"):
    def __init__(self, bot):
        self.bot=bot
        self.statsserver=bot.statsserver
        self.errorreport=self.statsserver.get_channel(blink.Config.errors())

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        return await self.handle(ctx,error)

    async def handle(self,ctx,error):
        """The event triggered when an error is raised while invoking a command.
        ctx   : Context
        error : Exception"""

        ignored=(commands.CommandNotFound,blink.SilentWarning,blink.IncorrectChannelError)
        error=getattr(error, 'original', error)

        if isinstance(error, ignored):
            return

        elif isinstance(error,commands.MissingRequiredArgument):
            try:
                await ctx.message.add_reaction("\U00002754")
                return await ctx.send_help(ctx.command)
            except discord.Forbidden:
                return

        elif isinstance(error,commands.TooManyArguments):
            try:
                await ctx.message.add_reaction("\U00002754")
                return await ctx.send_help(ctx.command)
            except discord.Forbidden:
                return

        elif isinstance(error,menus.CannotAddReactions):
            return await ctx.send(embed=discord.Embed(colour=15158332,title="I am unable to initialize the reaction menu. Please give me permissions to add reactions."))

        elif isinstance(error,commands.BotMissingPermissions):
            try:
                return await ctx.send(error)
            except discord.Forbidden:
                return
        elif isinstance(error, commands.DisabledCommand):
            return await ctx.send(embed=discord.Embed(colour=15158332,title=f'**`{ctx.command}`** has been disabled.'))

        elif isinstance(error, commands.MissingPermissions):
            return await ctx.send(embed=discord.Embed(colour=15158332,title=f'You do not have permission to use the command **`{ctx.command}`**'))

        elif isinstance(error, commands.NotOwner):
            try:
                return await ctx.message.add_reaction("\U000026d4")
            except discord.Forbidden:
                return

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.author.send(f'**`{ctx.command}`** can not be used in Private Messages.')
            except discord.Forbidden:
                return
        elif isinstance(error, discord.errors.Forbidden):
            try:
                return await ctx.send(embed=discord.Embed(colour=15158332,title="I do not have permission to do that."))
            except discord.Forbidden:
                return

        elif isinstance(error, commands.BadArgument):
            return await ctx.send(embed=discord.Embed(colour=15158332,title=str(error)))

        elif isinstance(error, commands.CommandOnCooldown):
            if ctx.author.id in self.bot.owner_ids:
                await ctx.reinvoke()
                return
            try:
                return await ctx.message.add_reaction("\U000023f2")
            except discord.Forbidden:
                return

        elif isinstance(error, blink.NoChannelProvided):
            return await ctx.send(embed=discord.Embed(colour=15158332,title='You must be in a voice channel or provide one to connect to.'))
        elif isinstance(error,commands.NSFWChannelRequired):
            return await ctx.send(embed=discord.Embed(colour=15158332,title="This command is locked to nsfw channels only."))

        elif isinstance(error,commands.MaxConcurrencyReached):
            return await ctx.send(embed=discord.Embed(colour=15158332,title=str(error)))

        elif isinstance(error,asyncpg.exceptions.PostgresError):
            return await ctx.send(embed=discord.Embed(colour=15158332,title=str(error)))

        elif isinstance(error,NoNodes):
            await self.bot.warn(error)
            return await ctx.send(embed=discord.Embed(colour=15158332,title="Music is temporarily unavailable right now. please try again later."))

        await ctx.send(embed=discord.Embed(title="Uh Oh! Something went wrong...",description="if this persists please contact the bot dev via ;support\nThis incident has been logged.",colour=discord.Colour.red()))
        await self.errorreport.send(f"Error occureed in guild: {ctx.guild or None} | {ctx.guild.id or None} channel: {ctx.channel.mention} | {ctx.channel.id} \nCommand: **`{ctx.message.content}`** " + "```" + str("\n".join(traceback.format_exception(type(error), error, error.__traceback__))) + f"```\nOCCURED AT : {datetime.datetime.utcnow().isoformat()}")


def setup(bot):
    bot.add_cog(CommandErrorHandler(bot))
