import json
import discord
from discord.ext import commands
import blink
from typing import Union


class Server(blink.Cog,name="Server"):
    def memberscheck(self):
        def predicate(self,ctx):
            if ctx.command.endswith("members"):
                return True
            elif ctx.author.guild_permissions.manage_roles:
                return True
            else:
                return False
        return commands.check(predicate)

    @commands.command(name="members")
    @commands.guild_only()
    @commands.bot_has_guild_permissions(send_messages=True,embed_links=True)
    @commands.check(memberscheck)
    async def members(self, ctx, *, term: Union[int,str]=None):
        """Shows members for a given role (or all)"""
        if not term:
            return await self.users(ctx)
        role = ctx.guild.get_role(term)
        if not role:
            role=await blink.searchrole(ctx.guild.roles,str(term))
        if not role:
            return await ctx.send("I could not find that role.")
        if len(role.members) > 35 or len(role.members) == 0:
            return await ctx.send(f"There are {len(role.members)} members with the role {role.name}")
        embed=discord.Embed(title=f"{role.name} - {len(role.members)}",colour=0xf5a6b9)
        embed.add_field(name="Members:", value=" ".join(m.mention for m in role.members), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="muted",aliases=["mutes","currentmutes"])
    @commands.guild_only()
    @commands.bot_has_guild_permissions(send_messages=True,embed_links=True)
    @commands.has_permissions(manage_roles=True)
    async def muted(self, ctx):
        """Shows currently muted members"""
        role=await blink.searchrole(ctx.guild.roles,"muted")
        if not role:
            return await ctx.send("I could not find the muted.")
        if len(role.members) == 0:
            return await ctx.send("There are no currently muted members.")
        embed=discord.Embed(title="Current mutes",colour=self.bot.colour)
        embed.add_field(name="Members:", value=" ".join(m.mention for m in role.members), inline=False)
        if len(embed) > 6000:
            return await ctx.send(f"There are {len(role.members)} people muted, which is too many for me to display.")
        await ctx.send(embed=embed)

    @commands.command(name="users",aliases=["membercount"])
    @commands.guild_only()
    @commands.bot_has_guild_permissions(send_messages=True,embed_links=True)
    async def users(self,ctx):
        """Shows the user count for the guild."""
        embed=discord.Embed(title=(ctx.guild.name + ":"),colour=self.bot.colour)
        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.add_field(name="Guild Members:", value=ctx.guild.member_count, inline=False)
        return await ctx.send(embed=embed)

    @commands.command(name="lock")
    @commands.guild_only()
    @commands.bot_has_guild_permissions(send_messages=True,embed_links=True,manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def lockchannel(self,ctx,channel:discord.TextChannel=None):
        """Locks a channel."""
        if not channel:
            channel=ctx.channel
        await channel.set_permissions(ctx.guild.default_role, overwrite=discord.PermissionOverwrite(send_messages=False))
        await ctx.send(f"Locked {channel.name} for all members.")

    @commands.command(name="unlock")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(send_messages=True,embed_links=True,manage_channels=True)
    async def unlocklockchannel(self,ctx,channel:discord.TextChannel=None):
        """Unlocks a channel."""
        if not channel:
            channel=ctx.channel
        await channel.set_permissions(ctx.guild.default_role, overwrite=discord.PermissionOverwrite(send_messages=True))
        await ctx.send(f"Unlocked {channel.name} for all members.")

    @commands.command(name="serverinfo",aliases=["si","server"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def serverinfo(self,ctx):
        """Shows info about a server"""
        g = ctx.guild

        embed=discord.Embed(colour=self.bot.colour)
        embed.set_author(name=g.name,icon_url=g.icon_url_as(static_format="png"))

        cd = g.created_at
        ge = str(g.explicit_content_filter)
        om = len(list(m for m in g.members if m.status == discord.Status.online))
        im = len(list(m for m in g.members if m.status == discord.Status.idle))
        dm = len(list(m for m in g.members if m.status == discord.Status.dnd))
        ofm = len(list(m for m in g.members if m.status == discord.Status.offline))
        admins = list(m for m in g.members if m.guild_permissions.administrator and not m.bot)
        mods = list(m for m in g.members if m.guild_permissions.manage_messages and not m.bot and m not in admins)
        adminbots = list(m for m in g.members if m.guild_permissions.administrator and m.bot)

        embed.add_field(inline=True,name="**Info**",value=f"**Created** {cd.year:04}/{cd.month}/{cd.day:02}\n**Region** {g.region}\n**Emojis** {len(g.emojis)}/{g.emoji_limit*2}\n**Upload Limit** {round(g.filesize_limit * 0.00000095367432)}MB\n**Verification level** {str(g.verification_level).capitalize()}\n**Media filtering** {'No one' if ge == 'Disabled' else 'No role' if ge =='no_role' else 'Everyone'}")
        embed.add_field(inline=True,name="**Members**",value=f"**All** {g.member_count}\n<:bonline:707359046122078249> {om}\n<:bidle:707359045971083315> {im}\n<:bdnd:707368559759720498> {dm}\n<:boffline:707359046138855550> {ofm}")
        embed.add_field(inline=True,name="**Staff**",value=f"**Owner** <@{g.owner_id}>\n**Admins** {len(admins)}\n**Mods** {len(mods)}\n**Admin Bots** {len(adminbots)}")
        embed.set_footer(text=f"Shard: {self.bot.cluster.identifier}{g.shard_id}")
        m = await ctx.send(embed=embed)

        if (await self.bot.session.head(f"https://disboard.org/server/{g.id}")).status == 200:
            disboard = f"[Disboard](https://disboard.org/server/{g.id})"
        else:
            disboard = None

        if (await self.bot.session.head(f"https://top.gg/servers/{g.id}")).status == 200:
            topgg = f"[Top.gg](https://top.gg/servers/{g.id})"
        else:
            topgg = None
        features = ' | '.join(m.replace('_',' ').lower().capitalize() for m in (f for f in g.features if f != 'MORE_EMOJI'))
        other = [
            f"**Unlocked Features** : {features if not features == '' else 'None'}",
            f"**Boosts** {g.premium_subscription_count} | **Boosters** {len(g.premium_subscribers)}",
            f"**Channels** {len(g.channels)} ({len(list(c for c in g.channels if isinstance(c,discord.TextChannel)))} Text, {len(list(c for c in g.channels if isinstance(c,discord.VoiceChannel)))} Voice, {len(list(c for c in g.channels if isinstance(c,discord.CategoryChannel)))} Category)",
            f"**Moderation requires 2FA** {'Yes' if g.mfa_level == 1 else 'No'}",
        ]
        if g.me.guild_permissions.ban_members:
            other.append('**Bans** ' + str(len(await g.bans())))
        if disboard or topgg:
            other.append(f"{disboard if disboard else ''} {topgg if topgg else ''}")
        embed.add_field(name='**Other**',value="\n".join(other),inline=False)
        return await m.edit(embed=embed)

    @commands.group(name="statusrole",aliases=["srole","sr"],invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True, manage_roles=True)
    async def status_role(self, ctx):
        """Manage status role, gives a user a role for having certain text in their status - eg pic perms for having a vanity in a users status"""
        async with ctx.cache:
            server = json.loads(ctx.cache.value["data"])

        if not server.get("status_role_enabled"):
            await ctx.send("Status role is not enabled")

        else:
            await ctx.send(embed=discord.Embed(title=f"Status role for {ctx.guild.name}", description=f"Role is <@&{server.get('status_role_id')}> , status is '{server.get('status_role_string')}'"))

    @status_role.command(name="enable",aliases=["on"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True, manage_roles=True)
    async def status_enable(self, ctx):
        """Enable status role"""
        async with ctx.cache:
            server = json.loads(ctx.cache.value["data"])

        if server.get("status_role_setup"):
            if server.get("status_role_enabled"):
                return await ctx.send("Status role is already enabled.")

            server["status_role_enabled"] = True
            await self.bot.DB.execute("UPDATE guilds SET data=$1 WHERE id=$2", json.dumps(server), ctx.guild.id)
            await ctx.cache.bot_invalidate(self.bot)
            await ctx.send("Status role is now enabled.")
        else:
            await ctx.send("Status role is not currently set up.")

    @status_role.command(name="disable",aliases=["off"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True, manage_roles=True)
    async def status_disable(self, ctx):
        """Disable status role"""
        async with ctx.cache:
            server = json.loads(ctx.cache.value["data"])

        if server.get("status_role_setup"):
            if not server.get("status_role_enabled"):
                return await ctx.send("Status role is already disabled.")
            server["status_role_enabled"] = False
            await self.bot.DB.execute("UPDATE guilds SET data=$1 WHERE id=$2", json.dumps(server), ctx.guild.id)
            await ctx.cache.bot_invalidate(self.bot)
            await ctx.send("Status role is now disabled.")
        else:
            await ctx.send("Status role is not currently set up.")

    @status_role.command(name="setup",aliases=["set","update"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True, manage_roles=True)
    async def status_setup(self,ctx, role:discord.Role, *, status):
        """Setup or change status roles"""
        async with ctx.cache:
            server = json.loads(ctx.cache.value["data"])
            server["status_role_string"] = status
            server["status_role_id"] = role.id
            server["status_role_setup"] = True
            await self.bot.DB.execute("UPDATE guilds SET data=$1 WHERE id=$2", json.dumps(server), ctx.guild.id)
            await ctx.cache.bot_invalidate(self.bot)
            await ctx.send("Configured status role, use `statusrole enable` to enable.")

    @commands.Cog.listener("on_member_update")
    async def presence_checker(self, before, after:discord.Member):
        if before.activity == after.activity:
            return
        data = self.bot.cache_or_create(f"guild-{before.guild.id}","SELECT data FROM guilds WHERE id=$1",(before.guild.id,))
        async with data:
            if not data.value:
                return
            server = json.loads(data.value["data"])

        role_valid = True
        if server.get("status_role_enabled"):
            role = after.guild.get_role(int(server["status_role_id"]))
            if not role:
                role_valid = False

            status_valid = False
            if isinstance(after.activity, discord.CustomActivity):
                if after.activity.name:
                    if server["status_role_string"].lower() in after.activity.name.lower():
                        status_valid = True

            if status_valid:
                if role not in after.roles:
                    try:
                        await after.add_roles(role,reason="Status role")
                    except discord.Forbidden:
                        role_valid = False
            else:
                if role in after.roles:
                    try:
                        await after.remove_roles(role,reason="Status role is no longer valid")
                    except discord.Forbidden:
                        role_valid = False

            if not role_valid:
                server["status_role_setup"] = False
                server["status_role_enabled"] = False
                await self.bot.DB.execute("UPDATE guilds SET data=$1 WHERE id=$2", json.dumps(server), after.guild.id)
                await data.bot_invalidate(self.bot)


def setup(bot):
    bot.add_cog(Server(bot,"server"))
