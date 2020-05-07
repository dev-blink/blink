import discord
from discord.ext import commands
import blink


# Checks if there is a muted role on the server and creates one if there isn't
async def mute(ctx, user, reason):
    role=discord.utils.get(ctx.guild.roles, name="Muted")
    if not role:  # checks if there is muted role
        try:  # creates muted role
            muted=await ctx.guild.create_role(name="Muted", reason="To use for muting")
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted, send_messages=False)
        except discord.Forbidden:
            return await ctx.send("I have no permissions to make a muted role")
        await user.add_roles(muted)  # adds newly created muted role
        await ctx.send(f"{user.mention} was muted for {reason}.")
    else:
        await user.add_roles(role)  # adds already existing muted role
        await ctx.send(f"{user.mention} was muted for {reason}.")


async def dmattempt(user,action,reason,guild):
    try:
        await user.send(f"You were {action} in {guild} for {reason}")
    except discord.Forbidden:
        pass


class Moderation(commands.Cog, name="Moderation"):
    """Commands used to moderate your guild"""

    def __init__(self, bot):
        self.bot=bot

    async def __error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(error)

    @commands.command(name="ban",aliases=["banish"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True,ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx, user: discord.Member=None,*,reason:str):
        """Bans a user."""
        reason=" ".join(reason)
        if reason == "":
            reason=None
        if not user:
            return await ctx.send("You must specify a user.")
        if not ctx.guild.owner == ctx.author:
            if user.top_role >= ctx.author.top_role:
                return await ctx.send("You are unable to sanction that user. (Check your roles)")
        try:
            await dmattempt(user,"banned",reason,ctx.guild.name)
            if reason:
                await ctx.guild.ban(user,reason=f"Banned by {ctx.author} for {reason}")
            else:
                await ctx.guild.ban(user, reason=f"By {ctx.author} for None Specified")
            await ctx.send(f"{user.mention} was banned for {reason}.")
        except discord.Forbidden:
            return await ctx.send("I am unable to ban that user, (discord.Forbidden)")

    @commands.command(name="unban",aliases=["unbanish"])
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True,ban_members=True)
    async def unban(self, ctx, *, username:int):
        """Unbans a user by their id."""
        if not username:
            return await ctx.send("You must specify a user.")
        try:
            banlist=await ctx.guild.bans()
        except discord.errors.Forbidden:
            await ctx.send("I do not have permission to unban that user.")
            return
        user=None
        for ban in banlist:
            if ban.user.id == username:
                user=ban.user
        if user is None:
            await ctx.send("User not banned.")
            return
        await ctx.guild.unban(user)
        await ctx.send("Unbanned user.")

    @commands.command(name="softban",aliases=["softbanish"])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True,ban_members=True)
    async def softban(self, ctx, user: discord.Member=None,*,reason:str=None):
        """Bans and unbans a member to delete their messages."""
        if not user:
            return await ctx.send("You must specify a user.")
        if not ctx.guild.owner == ctx.author:
            if user.top_role >= ctx.author.top_role:
                return await ctx.send("You are unable to sanction that user. (Check your roles)")

        try:
            await dmattempt(user,"kicked",reason,ctx.guild.name)
            if reason:
                await ctx.guild.ban(user, reason=f"By {ctx.author} for {reason}")
            else:
                await ctx.guild.ban(user, reason=f"By {ctx.author} for None Specified")
            await ctx.guild.unban(user, reason="Softbanned")
            await ctx.send(f"{user.mention} was softbanned for {reason}.")
        except discord.Forbidden:
            return await ctx.send("I am unable to softban that user, (discord.Forbidden)")

    @commands.command(name="mute",aliases=["silence"])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_roles=True)
    async def mute(self, ctx, user: discord.Member=None,*,reason:str=None):
        """Mutes a user."""
        if not user:
            return await ctx.send("You must specify a user.")
        if not ctx.guild.owner == ctx.author:
            if user.top_role >= ctx.author.top_role:
                return await ctx.send("You are unable to sanction that user. (Check your roles)")
        """Mutes a user."""
        await mute(ctx, user, reason or "being annoying")

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True,kick_members=True)
    @commands.guild_only()
    async def kick(self, ctx, user: discord.Member=None,*,reason:str):
        """Kicks a user."""
        reason=" ".join(reason)
        if reason == "":
            reason=None
        if not user:
            return await ctx.send("You must specify a user")
        if not ctx.guild.owner == ctx.author:
            if user.top_role >= ctx.author.top_role:
                return await ctx.send("You are unable to sanction that user. (Check your roles)")

        try:
            await dmattempt(user,"kicked",reason,ctx.guild.name)
            if reason:
                await ctx.guild.kick(user, reason=f"By {ctx.author} for {reason}")
                await ctx.send(f"{user.mention} was kicked for {reason}.")
            else:
                await ctx.guild.kick(user, reason=f"By {ctx.author} for None Specified")
                await ctx.send(f"{user.mention} was kicked for {reason}.")
        except discord.Forbidden:
            return await ctx.send("I am unable to kick that user, (discord.Forbidden)")

    @commands.command(name="purge",aliases=["prune"])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_messages=True)
    async def purge(self, ctx, limit: int):
        """Bulk deletes messages."""

        await ctx.channel.purge(limit=limit + 1)  # also deletes your own message
        await ctx.send(f"Bulk deleted `{limit}` messages",delete_after=5)

    @commands.command(name="unmute")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_roles=True)
    async def unmute(self, ctx, user: discord.Member=None):
        """Unmutes a muted user."""
        if not user:
            return await ctx.send("You must specify a user.")
        term="muted"
        role=await blink.searchrole(ctx.guild.roles,term)
        if not role:
            return await ctx.send("I could not find the muted role..")
        await user.remove_roles(role)
        await ctx.send(f"{user.mention} has been unmuted")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_channels=True)
    async def block(self, ctx, user: discord.Member=None):
        """Blocks a user from chatting in current channel."""

        if not user:
            return await ctx.send("You must specify a user")
        if not ctx.guild.owner == ctx.author:
            if user.top_role >= ctx.author.top_role:
                return await ctx.send("You are unable to sanction that user. (Check your roles)")

        await ctx.channel.set_permissions(user, send_messages=False) # sets permissions for current channel
        await ctx.send(f"{user.mention} was blocked.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_channels=True)
    async def unblock(self, ctx, user: discord.Member=None):
        """Unblocks a user from current channel."""

        if not user:
            return await ctx.send("You must specify a user")

        await ctx.channel.set_permissions(user, send_messages=None) # gives back send messages permissions
        await ctx.send(f"{user.mention} was unblocked.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_messages=True)
    async def clean(self,ctx, user: discord.Member=None,count:int =None):
        """Cleans a set amount of messages from a user (defaults to bot users and 50 messages)"""
        # CLEAN COMMAND CHECKS
        def checkbot(m):
            return m.author.bot

        def checkuser(m):
            return m.author == user

        if user is not None:
            cleanbot=False
        else:
            cleanbot=True

        if not count:
            if not cleanbot:
                count=30
            else:
                count=50
        if not cleanbot:
            await ctx.channel.purge(limit=count, check=checkuser)
            await ctx.message.delete()
            return await ctx.send(f"Cleaned {count} messages from user: {user.mention}",delete_after=4)
        else:
            try:
                await ctx.channel.purge(limit=count, check=checkbot)
            except discord.HTTPException:
                await ctx.send("An error occured while attempting to purge\n(Probably attempting to purge more than 14 days ago)")
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass
            return await ctx.send(f"Cleaned {count} messages from bots",delete_after=4)


def setup(bot):
    bot.add_cog(Moderation(bot))
