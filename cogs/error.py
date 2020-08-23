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
        self.bot._cogs.error = self
        self.nocooldown = bot.owner_ids + []

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        return await self.handle(ctx,error)

    async def handle(self,ctx,error):
        ignored=(commands.CommandNotFound,blink.SilentWarning,blink.IncorrectChannelError)
        error=getattr(error, 'original', error)

        if ctx.prefix == "":
            if isinstance(error,commands.UserInputError):
                return

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
            if ctx.author.id in self.nocooldown:
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
            await self.bot.warn("no nodes "+ error,False)
            return await ctx.send(embed=discord.Embed(colour=15158332,title="Music is temporarily unavailable right now. please try again later."))

        elif isinstance(error,commands.UnexpectedQuoteError):
            return await ctx.send("Looks like you tried to use a quote in an argument (don't do that) it's hard to distinguish arguments")
        #
        # Error reporting
        #
        await ctx.send(embed=discord.Embed(title="Uh Oh! Something went wrong...",description="this should not have happened.. contact the dev via ;support\nThis incident has been logged.",colour=discord.Colour.red()))
        if ctx.guild:
            guild = f"{ctx.guild.id} -- {ctx.guild.name}"
        else:
            guild = "no guild"
        if isinstance(ctx.channel,discord.DMChannel):
            channel = f"DM WITH {ctx.channel.recipient}"
        else:
            channel = f"{ctx.channel.id} -- #{ctx.channel.name} ({ctx.channel.mention})"
        await self.bot.cluster.log_errors(f"Error occureed in guild: {guild} | channel: {channel} | author {ctx.author} {ctx.author.id} ({ctx.author.mention})\nCommand: **`{ctx.message.content}`** " + "```" + str("\n".join(traceback.format_exception(type(error), error, error.__traceback__))) + f"```\nOCCURED AT : {datetime.datetime.utcnow()}")


def setup(bot):
    bot.add_cog(CommandErrorHandler(bot))
