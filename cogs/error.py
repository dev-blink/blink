# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


import traceback
from discord.ext import commands, menus
import discord
import blink
import datetime
import aiohttp
import asyncpg
import secrets
from wavelink import ZeroConnectedNodes as NoNodes


async def sendEmbedError(ctx,message):
    embed = discord.Embed(colour=15158332)
    if len(message) < 256:
        embed.title=message
    else:
        embed.title=":x: Error"
        embed.description=message
    await ctx.send(embed=embed)


class CommandErrorHandler(blink.Cog,name="ErrorHandler"):
    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        self.nocooldown = self.bot.owner_ids + []

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
                await ctx.send_help(ctx.command)
                return await ctx.message.add_reaction("\U00002754")
            except discord.Forbidden:
                return

        elif isinstance(error,commands.TooManyArguments):
            try:
                await ctx.send_help(ctx.command)
                return await ctx.message.add_reaction("\U00002754")
            except discord.Forbidden:
                return

        elif isinstance(error,menus.CannotAddReactions):
            return await sendEmbedError(ctx,"I am unable to initialize the reaction menu. Please give me permissions to add reactions.")

        elif isinstance(error, aiohttp.ClientOSError):
            await sendEmbedError(ctx, "There was a temporary network issue while completing your command, usually this means the command finished, but failed to send a message at the end.")

        elif isinstance(error,commands.BotMissingPermissions):
            try:
                return await ctx.send(error)
            except discord.Forbidden:
                return
        elif isinstance(error, commands.DisabledCommand):
            return await sendEmbedError(ctx,f'**`{ctx.command}`** has been disabled.')

        elif isinstance(error, commands.MissingPermissions):
            return await sendEmbedError(ctx,f'You do not have permission to use the command **`{ctx.command}`**')

        elif isinstance(error, commands.NotOwner):
            try:
                return await ctx.message.add_reaction("\U000026d4")
            except discord.Forbidden:
                return

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                return await sendEmbedError(ctx,f'**`{ctx.command}`** can not be used in Private Messages.')
            except discord.Forbidden:
                return
        elif isinstance(error, discord.errors.Forbidden):
            try:
                return await sendEmbedError(ctx,"I do not have permission to do that.")
            except discord.Forbidden:
                return

        elif isinstance(error, commands.BadArgument):
            return await sendEmbedError(ctx,str(error))

        elif isinstance(error, commands.CommandOnCooldown):
            if ctx.author.id in self.nocooldown:
                await ctx.reinvoke()
                return
            try:
                return await ctx.message.add_reaction("\U000023f2")
            except discord.Forbidden:
                return

        elif isinstance(error, blink.NoChannelProvided):
            return await sendEmbedError(ctx,'You must be in a voice channel or provide one to connect to.')
        elif isinstance(error,commands.NSFWChannelRequired):
            return await sendEmbedError(ctx,"This command is locked to nsfw channels only.")

        elif isinstance(error,commands.MaxConcurrencyReached):
            return await sendEmbedError(ctx,str(error))

        elif isinstance(error,asyncpg.exceptions.PostgresError):
            if ctx.author.id in self.bot.owner_ids:
                return await sendEmbedError(ctx,str(error))

        elif isinstance(error,NoNodes):
            await self.bot.warn("no nodes",False)
            return await sendEmbedError(ctx,"Music is temporarily unavailable right now. please try again later.")

        elif isinstance(error,commands.UnexpectedQuoteError):
            return await sendEmbedError(ctx,"Looks like you tried to use a quote in an argument (don't do that) it makes it impossible to distinguish arguments.")
        #
        # Error reporting
        #
        if ctx.author.id in self.bot.owner_ids:
            await ctx.send(f"{error.__class__.__qualname__} - {error}")
        await ctx.send(embed=discord.Embed(title="Uh Oh! Something went drastically wrong...",description="This shouldnt happen. Please contact us in the [support server](https://discord.gg/d23VBaR)",colour=discord.Colour.red()).set_footer(text="This incident has been logged."))
        if ctx.guild:
            guild = f"{ctx.guild.id} -- {ctx.guild.name}"
        else:
            guild = "no guild"
        if isinstance(ctx.channel,discord.DMChannel):
            channel = f"DM WITH {ctx.channel.recipient}"
        else:
            channel = f"{ctx.channel.id} -- #{ctx.channel.name} ({ctx.channel.mention})"

        tb = '\n'.join(traceback.format_exception(type(error), error, error.__traceback__))
        embed = discord.Embed(description=f"Guild: {guild}\nChannel: {channel}\nAuthor: {ctx.author} {ctx.author.id} ({ctx.author.mention})\nCommand: **`{ctx.message.content}`**",colour=discord.Colour.red(),timestamp=datetime.datetime.utcnow())
        async with aiohttp.ClientSession() as cs:
            async with cs.post("https://api.github.com/gists", headers={"Authorization":"token "+ secrets.gist}, json={"public":False, "files":{"traceback.txt":{"content":tb}}}) as gist:
                data = await gist.json()
                embed.set_author(name="UNCAUGHT EXCEPTION",url=data["html_url"])

        await self.bot.cluster.log_errors(embed=embed)


def setup(bot):
    bot.add_cog(CommandErrorHandler(bot,"error"))
