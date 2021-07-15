# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


import discord
from discord.ext import commands
import blink
import aiohttp
import asyncio
import contextlib
from io import BytesIO
from typing import Union
import secrets


class Server(blink.Cog, name="Server"):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._transform_cooldown = commands.CooldownMapping.from_cooldown(
            1, 30, commands.BucketType.channel)

    def memberscheck(self):
        def predicate(self, ctx):
            if ctx.command.endswith("members"):
                return True
            elif ctx.author.guild_permissions.manage_roles:
                return True
            else:
                return False
        return commands.check(predicate)

    @commands.command(name="members")
    @commands.guild_only()
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    @commands.check(memberscheck)
    async def members(self, ctx, *, term: Union[int, str] = None):
        """Shows members for a given role (or all)"""
        if not term:
            return await self.users(ctx)
        role = ctx.guild.get_role(term)
        if not role:
            role = await blink.searchrole(ctx.guild.roles, str(term))
        if not role:
            return await ctx.send("I could not find that role.")
        if len(role.members) > 35 or len(role.members) == 0:
            return await ctx.send(f"There are {len(role.members)} members with the role {role.name}")
        embed = discord.Embed(
            title=f"{role.name} - {len(role.members)}", colour=0xf5a6b9)
        embed.add_field(name="Members:", value=" ".join(
            m.mention for m in role.members), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="muted", aliases=["mutes", "currentmutes"])
    @commands.guild_only()
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def muted(self, ctx):
        """Shows currently muted members"""
        role = await blink.searchrole(ctx.guild.roles, "muted")
        if not role:
            return await ctx.send("I could not find the muted.")
        if len(role.members) == 0:
            return await ctx.send("There are no currently muted members.")
        embed = discord.Embed(title="Current mutes", colour=self.bot.colour)
        embed.add_field(name="Members:", value=" ".join(str(m)
                        for m in role.members), inline=False)
        if len(embed.description) > 2048:
            return await ctx.send(f"There are {len(role.members)} people muted, which is too many for me to display.")
        await ctx.send(embed=embed)

    @commands.command(name="users", aliases=["membercount"])
    @commands.guild_only()
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    async def users(self, ctx):
        """Shows the user count for the guild."""
        embed = discord.Embed(title=(ctx.guild.name + ":"),
                              colour=self.bot.colour)
        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.add_field(name="Guild Members:",
                        value=ctx.guild.member_count, inline=False)
        return await ctx.send(embed=embed)

    @commands.command(name="lock")
    @commands.guild_only()
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True, manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def lockchannel(self, ctx, channel: discord.TextChannel = None):
        """Locks a channel."""
        if not channel:
            channel = ctx.channel
        await channel.set_permissions(ctx.guild.default_role, overwrite=discord.PermissionOverwrite(send_messages=False))
        await ctx.send(f"Locked {channel.name} for all members.")

    @commands.command(name="unlock")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True, manage_channels=True)
    async def unlockchannel(self, ctx, channel: discord.TextChannel = None):
        """Unlocks a channel."""
        if not channel:
            channel = ctx.channel
        await channel.set_permissions(ctx.guild.default_role, overwrite=discord.PermissionOverwrite(send_messages=True))
        await ctx.send(f"Unlocked {channel.name} for all members.")

    @commands.command(name="serverinfo", aliases=["si", "server"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def serverinfo(self, ctx):
        """Shows info about a server"""
        g = ctx.guild

        embed = discord.Embed(colour=self.bot.colour)
        embed.set_author(
            name=g.name, icon_url=g.icon_url_as(static_format="png"))

        cd = g.created_at
        ge = str(g.explicit_content_filter)
        om = im = dm = ofm = admins = mods = adminbots = bots = 0

        for m in g.members:
            if m.status == discord.Status.online:
                om += 1
            elif m.status == discord.Status.idle:
                im += 1
            elif m.status == discord.Status.dnd:
                dm += 1
            elif m.status == discord.Status.offline:
                ofm += 1
            if m.guild_permissions.administrator:
                if m.bot:
                    adminbots += 1
                else:
                    admins += 1
            elif m.guild_permissions.manage_messages and not m.bot:
                mods += 1
            if m.bot:
                bots += 1

        embed.add_field(inline=True, name="**Info**",
                        value=f"**Created** {cd.year:04}/{cd.month}/{cd.day:02}\n**Region** {g.region}\n**Emojis** {len(g.emojis)}/{g.emoji_limit*2}\n**Upload Limit** {round(g.filesize_limit * 0.00000095367432)}MB\n**Verification level** {str(g.verification_level).capitalize()}\n**Media filtering** {'No one' if ge == 'Disabled' else 'No role' if ge =='no_role' else 'Everyone'}")
        embed.add_field(inline=True, name="**Members**",
                        value=f"**All** {g.member_count}\n<:bonline:707359046122078249> {om}\n<:bidle:707359045971083315> {im}\n<:bdnd:707368559759720498> {dm}\n<:boffline:707359046138855550> {ofm}")
        embed.add_field(inline=True, name="**Staff**",
                        value=f"**Owner** {g.owner}\n**Admins** {admins}\n**Mods** {mods}\n**Admin Bots** {adminbots}\n**Bots** {bots}")
        embed.set_footer(
            text=f"Shard: {self.bot.cluster.identifier}{g.shard_id}")

        if g.banner:
            embed.set_image(url=g.banner_url_as(format="png", size=128))
        m = await ctx.send(embed=embed)

        if (await self.bot.session.head(f"https://disboard.org/server/{g.id}")).status == 200:
            disboard = f"[Disboard](https://disboard.org/server/{g.id})"
        else:
            disboard = None

        if (await self.bot.session.head(f"https://top.gg/servers/{g.id}")).status == 200:
            topgg = f"[Top.gg](https://top.gg/servers/{g.id})"
        else:
            topgg = None
        features = ' | '.join(m.replace('_', ' ').lower().capitalize()
                              for m in (f for f in g.features if f != 'MORE_EMOJI'))
        other = [
            f"**Unlocked Features** : {features if not features == '' else 'None'}",
            f"**Boosts** {g.premium_subscription_count} | **Boosters** {len(g.premium_subscribers)}",
            f"**Channels** {len(g.channels)} ({len(list(c for c in g.channels if isinstance(c,discord.TextChannel)))} Text, {len(list(c for c in g.channels if isinstance(c,discord.VoiceChannel)))} Voice, {len(list(c for c in g.channels if isinstance(c,discord.CategoryChannel)))} Category)",
            f"**Moderation requires 2FA** {'Yes' if g.mfa_level == 1 else 'No'}",
        ]
        if g.me.guild_permissions.ban_members:
            other.append('**Bans** ' + str(len(await g.bans())))
        if disboard or topgg:
            other.append(
                f"{disboard if disboard else ''} {topgg if topgg else ''}")
        embed.add_field(name='**Other**', value="\n".join(other), inline=False)
        return await m.edit(embed=embed)

    @commands.command(name="servericon", aliases=["sicon", "icon"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def server_icon(self, ctx):
        if ctx.guild.icon is None:
            return await ctx.send("Guild has no icon.")
        embed = discord.Embed(title=ctx.guild.name, colour=self.bot.colour)
        embed.set_image(url=ctx.guild.icon_url_as(static_format="png"))
        await ctx.send(embed=embed)

    @commands.group(name="statusrole", aliases=["srole", "sr"], invoke_without_command=True)
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def status_role(self, ctx):
        """Manage status role, gives a user a role for having certain text in their status - eg pic perms for having a vanity in a users status"""
        async with ctx.cache:
            server = ctx.cache.value

        if not server.get("status_role_enabled"):
            await ctx.send_help(ctx.command)

        else:
            await ctx.send(embed=discord.Embed(title=f"Status role for {ctx.guild.name}", description=f"Role is <@&{server.get('status_role_id')}> , status is '{server.get('status_role_string')}'", colour=self.bot.colour).set_footer(text="use statusrole help for info"))

    @status_role.command(name="enable", aliases=["on"])
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def status_enable(self, ctx):
        """Enable status role"""
        async with ctx.cache:
            server = ctx.cache.value

        if server.get("status_role_setup"):
            if server.get("status_role_enabled"):
                return await ctx.send("Status role is already enabled.")

            server["status_role_enabled"] = True
            await ctx.cache.save(ctx.guild.id, self.bot)
            await ctx.send("Status role is now enabled.")
        else:
            await ctx.send("Status role is not currently set up.")

    @status_role.command(name="disable", aliases=["off"])
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def status_disable(self, ctx):
        """Disable status role"""
        async with ctx.cache:
            server = ctx.cache.value

        if server.get("status_role_setup"):
            if not server.get("status_role_enabled"):
                return await ctx.send("Status role is already disabled.")
            server["status_role_enabled"] = False
            await ctx.cache.save(ctx.guild.id, self.bot)
            await ctx.send("Status role is now disabled.")
        else:
            await ctx.send("Status role is not currently set up.")

    @status_role.command(name="setup", aliases=["set", "update"])
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def status_setup(self, ctx, role: discord.Role, *, status):
        """Setup or change status roles"""
        async with ctx.cache:
            server = ctx.cache.value
            server["status_role_string"] = status
            server["status_role_id"] = role.id
            server["status_role_setup"] = True
            await ctx.cache.save(ctx.guild.id, self.bot)
            await ctx.send("Configured status role, use `statusrole enable` to enable.")

    @commands.group(name="prefix", aliases=["prefixes"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def prefixes(self, ctx):
        """Show guild prefixes"""
        async with ctx.cache:
            prefixes = ctx.cache.value.get(
                "prefixes") or self.bot.default_prefixes
            embed = discord.Embed(description="\n".join(
                prefixes), colour=self.bot.colour)
        embed.set_author(name=f"Prefixes for {ctx.guild}", icon_url=ctx.guild.icon_url_as(
            static_format="png"))
        embed.set_footer(
            text=f"Hint: admins see '{ctx.clean_prefix}help prefix' for info on changing prefixes")
        await ctx.send(embed=embed)

    @prefixes.command(name="add", aliases=["set"])
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_guild_permissions(manage_guild=True)
    async def add_prefix(self, ctx, *, prefix: str):
        """Add a guild prefix"""
        maxlen = 7
        prefix = prefix.strip()
        async with ctx.cache:
            if not ctx.cache.value.get("prefixes"):
                ctx.cache.value["prefixes"] = self.bot.default_prefixes
            if len(ctx.cache.value["prefixes"]) >= maxlen:
                await ctx.send(f"This guild already has the maximum of {maxlen} prefixes, please remove some before adding new ones")
            elif len(prefix) > 10:
                await ctx.send("Maximum of 10 characters please.")
            else:
                ctx.cache.value["prefixes"].append(prefix)
                await ctx.send(f"Added the prefix `{prefix}`")
                return await ctx.cache.save(ctx.guild.id, self.bot)
            await ctx.cache.bot_invalidate(self.bot)

    @prefixes.command(name="remove", aliases=["delete", "del"])
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_guild_permissions(manage_guild=True)
    async def remove_prefix(self, ctx, *, prefix: str):
        """Remove a guild prefix"""
        prefix = prefix.strip()
        async with ctx.cache:
            if not ctx.cache.value.get("prefixes"):
                ctx.cache.value["prefixes"] = self.bot.default_prefixes
            if len(ctx.cache.value["prefixes"]) == 1:
                await ctx.send("There must be atleast 1 prefix")
            elif prefix in ctx.cache.value["prefixes"]:
                ctx.cache.value["prefixes"].remove(prefix)
                await ctx.send(f"Removed the prefix `{prefix}`")
                return await ctx.cache.save(ctx.guild.id, self.bot)
            else:
                await ctx.send("That is not currently a server prefix")
            await ctx.cache.bot_invalidate(self.bot)

    @prefixes.command(name="reset", aliases=["default", "clear"])
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_guild_permissions(manage_guild=True)
    async def reset_prefix(self, ctx):
        """Reset prefixes to the default prefixes"""
        async with ctx.cache:
            if ctx.cache.value.get("prefixes"):
                del ctx.cache.value["prefixes"]
                await ctx.cache.save(ctx.guild.id, self.bot)
            await ctx.send("Guild prefixes have been reset to default")

    @commands.Cog.listener("on_member_update")
    async def presence_checker(self, before, after: discord.Member):
        if before.activity == after.activity:
            return
        data = self.bot.cache_or_create(
            f"guild-{before.guild.id}", "SELECT data FROM guilds WHERE id=$1", (before.guild.id,))
        async with data:
            if not data.value:
                return
            server = data.value

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
                        await after.add_roles(role, reason="Status role")
                    except discord.Forbidden:
                        role_valid = False
            else:
                if role in after.roles:
                    try:
                        await after.remove_roles(role, reason="Status role is no longer valid")
                    except discord.Forbidden:
                        role_valid = False

            if not role_valid:
                server["status_role_setup"] = False
                server["status_role_enabled"] = False
                await data.cache.save(after.guild.id, self.bot)

    @commands.Cog.listener("on_message")
    async def mov_wrapper(self, message):
        async with self.bot.cache_or_create("blacklist-transform", "SELECT snowflakes FROM blacklist WHERE scope=$1", ("transform",)) as blacklist:
            if message.author.id in blacklist.value["snowflakes"]:
                return
        p = message.channel.permissions_for(message.guild.me)
        if not (p.manage_messages and p.attach_files and p.send_messages and p.add_reactions):
            return

        if message.attachments:
            attachment = message.attachments[0]
            if attachment.filename.endswith((".mov", ".mp4")):
                if attachment.height:
                    return
                if attachment.content_type not in ["video/quicktime", "video/mp4"]:
                    return
                if attachment.size > 5 * (10**6):
                    return
                bucket = self._transform_cooldown.get_bucket(message)
                if bucket.update_rate_limit():
                    with contextlib.suppress(discord.Forbidden):
                        await message.add_reaction("⏳")
                    return

                task = self.bot.loop.create_task(self.mov_mp4(message))

                with contextlib.suppress(asyncio.TimeoutError):
                    await self.bot.wait_for("message_delete", check=lambda m: m.id == message.id, timeout=60)
                task.cancel()
                del task

    async def mov_mp4(self, message: discord.Message):
        with contextlib.suppress(asyncio.CancelledError):
            attachment = message.attachments[0]

            check = await message.channel.send(reference=message, content="looks like your video is broken, would you like me to try and fix it for you ?")
            await check.add_reaction("✔")
            await check.add_reaction("✖")

            try:
                react = await self.bot.wait_for("raw_reaction_add", check=lambda p: p.message_id == check.id and p.user_id == message.author.id and str(p.emoji) in ("✔", "✖"), timeout=10)
            except asyncio.TimeoutError:
                return await check.delete()
            else:
                if str(react.emoji) == "✖":
                    return await check.delete()

            await check.edit(content="working on it...")
            json = {
                "input": [{
                    "type": "remote",
                    "source": attachment.url
                }],
                "conversion": [{
                    "target": "mp4"
                }]
            }
            async with aiohttp.ClientSession() as cs:
                async with cs.post("https://api2.online-convert.com/jobs", headers={"X-Oc-Api-Key": secrets.converter}, json=json) as req:
                    if not req.status == 201:
                        await self.bot.warn(f"Error in video convert - http {req.status}", False)
                        return await check.edit(content="This service is temporarily unavailable. [HTTP]")
                    response = await req.json()
                    id = response["id"]
                try:
                    for limiter in range(30):
                        async with cs.get(f"https://api2.online-convert.com/jobs/{id}", headers={"X-Oc-Api-Key": secrets.converter}) as req:
                            json = await req.json()

                        if json.get("errors"):
                            await self.bot.warn(f"Error {req.status} in video convert: {json['errors']}", False)
                            return await check.edit(content="This service is temporarily unavailable. [CONVERT]")

                        if not json["output"]:
                            if limiter == 29:
                                async with cs.delete(f"https://api2.online-convert.com/jobs/{id}", headers={"X-Oc-Api-Key": secrets.converter}) as req:
                                    await self.bot.warn(f"Cancelled job {id} {message} for 30s limit", False)
                                    return await check.edit(content="This service is temporarily unavailable. [TIMEOUT]")
                            await asyncio.sleep(1)
                            continue

                        break
                except asyncio.CancelledError:
                    async with cs.delete(f"https://api2.online-convert.com/jobs/{id}", headers={"X-Oc-Api-Key": secrets.converter}) as req:
                        return

                if not json["output"]:
                    return

                async with cs.get(json["output"][0]["uri"]) as req:
                    data = BytesIO(await req.read())

                if len(data.getbuffer()) > message.guild.filesize_limit:
                    await check.delete()
                    return await message.channel.send("looks like that video was too big for me to upload")
                file = discord.File(data, filename="video.mp4")
                msg = await message.channel.send(content="This is a beta feature, please contact us in the support server if you have any feedback.", file=file, reference=message)
                await check.delete()
                await msg.add_reaction("🗑")

                with contextlib.suppress(asyncio.TimeoutError):
                    await self.bot.wait_for("raw_reaction_add", check=lambda p: str(p.emoji) == "🗑" and p.user_id == message.author.id and p.message_id == msg.id, timeout=300)
                    await msg.delete()


def setup(bot):
    bot.add_cog(Server(bot, "server"))
