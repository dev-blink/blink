import discord
from discord.ext import commands
import blink


# Checks if there is a muted role on the server and creates one if there isn't
async def mute(ctx, user, reason):
    role=await blink.searchrole(ctx.guild.roles,"Muted")
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
    if user.bot:
        return False
    if not isinstance(user,discord.Member):
        return False
    try:
        await user.send(f"You were {action} in {guild} for {reason}")
    except discord.HTTPException:
        return False
    return True


class Moderation(blink.Cog, name="Moderation"):
    """Commands used to moderate your guild"""

    @commands.Cog.listener("on_guild_channel_create")
    async def appendmutes(self,channel):
        """Deny permissions for muted to speak."""
        if not isinstance(channel, discord.TextChannel):
            return
        if not channel.guild.me.guild_permissions.manage_channels:
            return
        r = await blink.searchrole(channel.guild.roles, "Muted")
        if r:
            overwrites = channel.overwrites
            overwrites[r] = discord.PermissionOverwrite(send_messages=False)
            await channel.edit(overwrites=overwrites)

    async def privcheck(self,ctx,user):
        if not user:
            await ctx.send("You must specify a user.")
            raise blink.SilentWarning()

        if user.id == ctx.guild.owner_id:
            await ctx.send("That's the owner..")
            raise blink.SilentWarning()

        if user == ctx.author:
            await ctx.send("You cannot sanction yourself.")
            raise blink.SilentWarning()

        if not isinstance(user,discord.Member):
            return True

        if not ctx.guild.owner == ctx.author:
            if user.top_role >= ctx.author.top_role:
                await ctx.send("You are unable to sanction that user.")
                raise blink.SilentWarning()

        if user.top_role >= ctx.guild.me.top_role:
            await ctx.send("I cannot sanction that user. (check my role position)")
            raise blink.SilentWarning()

    @commands.command(name="ban",aliases=["banish"])
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True,ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx,user: discord.User,*,reason:str="unspecified"):
        """Bans a user."""
        await self.privcheck(ctx,user)
        if user == self.bot.user:
            await ctx.send("I cant do that. So i will leave instead.")
            return await ctx.guild.leave()
        try:
            dm = await dmattempt(user,"banned",reason,ctx.guild.name)
            await ctx.guild.ban(user,reason=f"Banned by {ctx.author} for {reason}")
            await ctx.send(f"{user.mention} was banned for {reason}. {'(I could not dm them about this)' if not dm else ''}")
        except discord.Forbidden:
            return await ctx.send("I am unable to sanction that user. (this probably shouldn't have happened (report it?))")

    @commands.command(name="unban",aliases=["unbanish"])
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True,ban_members=True)
    async def unban(self, ctx, *, user:discord.User):
        """Unbans a user."""
        try:
            await ctx.guild.unban(user)
        except discord.NotFound:
            return await ctx.send("User is not banned.")
        await ctx.send(f"Unbanned {user}")

    @commands.command(name="softban",aliases=["softbanish"])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True,ban_members=True)
    async def softban(self, ctx, user: discord.Member,*, reason:str="unspecified"):
        """Bans and unbans a member to delete their messages."""
        await self.privcheck(ctx,user)
        if user == self.bot.user:
            return await ctx.send("I cant do that.")

        try:
            dm = await dmattempt(user,"kicked",reason,ctx.guild.name)
            await ctx.guild.ban(user, reason=f"By {ctx.author} for {reason}")
            await ctx.guild.unban(user, reason="Softbanned")
            await ctx.send(f"{user.mention} was softbanned for {reason}. {'(I could not dm them about this)' if not dm else ''}")
        except discord.Forbidden:
            return await ctx.send("I am unable to sanction that user. (this probably shouldn't have happened (report it?))")

    @commands.command(name="mute",aliases=["silence"])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_roles=True)
    async def mute(self, ctx,user: discord.Member, *, reason:str="unspecified"):
        """Mutes a user."""
        await self.privcheck(ctx,user)
        await mute(ctx, user, reason or "being annoying")

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True,kick_members=True)
    @commands.guild_only()
    async def kick(self, ctx, user: discord.Member,*,reason:str="unspecified"):
        """Kicks a user."""
        await self.privcheck(ctx,user)
        if user == self.bot.user:
            return await ctx.guild.leave()

        try:
            dm = await dmattempt(user,"kicked",reason,ctx.guild.name)
            await ctx.guild.kick(user, reason=f"By {ctx.author} for {reason}")
            await ctx.send(f"{user.mention} was kicked for {reason}. {'(I could not dm them about this)' if not dm else ''}")
        except discord.Forbidden:
            return await ctx.send("I am unable to sanction that user. (this probably shouldn't have happened (report it?))")

    @commands.command(name="purge",aliases=["prune"])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_messages=True)
    async def purge(self, ctx, limit: int):
        """Bulk deletes messages."""
        if limit > 1000:
            limit = 1000
        try:
            await ctx.channel.purge(limit=limit + 1)  # also deletes your own message
        except Exception:
            return await ctx.send("Unable to purge those messages.")
        await ctx.send(f"Bulk deleted `{limit}` messages",delete_after=5)

    @commands.command(name="unmute")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_roles=True)
    async def unmute(self, ctx, *, user: discord.Member):
        """Unmutes a muted user."""
        role=await blink.searchrole(user.roles,"muted")
        if not role:
            return await ctx.send("That user isnt muted, or I couldn't find the muted role")
        await user.remove_roles(role)
        await ctx.send(f"{user.mention} has been unmuted")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_channels=True)
    async def block(self, ctx, *, user: discord.Member):
        """Blocks a user from chatting in current channel."""
        await self.privcheck(ctx,user)
        await ctx.channel.set_permissions(user, send_messages=False) # sets permissions for current channel
        await ctx.send(f"{user.mention} was blocked.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_channels=True)
    async def unblock(self, ctx, *, user: discord.Member):
        """Unblocks a user from current channel."""
        await ctx.channel.set_permissions(user, send_messages=None) # gives back send messages permissions
        await ctx.send(f"{user.mention} was unblocked.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_messages=True)
    async def clean(self,ctx,user: discord.Member=None,*,count:int =None):
        """Cleans a set amount of messages from a user (defaults to bots and 50 messages)"""
        if count:
            if count > 100:
                count = 100

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
            try:
                await ctx.channel.purge(limit=count, check=checkuser)
                await ctx.message.delete()
            except Exception as e:
                if str(e) == "400 Bad Request (error code: 50034): You can only bulk delete messages that are under 14 days old":
                    return await ctx.send("I cannot purge messages older than 14 days")
                else:
                    try:
                        raise
                    except discord.errors.NotFound:
                        pass
                    else:
                        raise
            return await ctx.send(f"Cleaned {count} messages from user: {user.mention}",delete_after=4)
        else:
            try:
                await ctx.channel.purge(limit=count, check=checkbot)
            except Exception as e:
                if str(e) == "400 Bad Request (error code: 50034): You can only bulk delete messages that are under 14 days old":
                    return await ctx.send("I cannot purge messages older than 14 days")
                else:
                    raise
            try:
                await ctx.message.delete()
            except Exception:
                pass
            return await ctx.send(f"Cleaned {count} messages from bots",delete_after=4)


def setup(bot):
    bot.add_cog(Moderation(bot,"mod"))
