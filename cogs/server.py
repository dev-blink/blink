import discord
from discord.ext import commands
from discord.utils import find
import blink


class Server(commands.Cog,name="Server"):
    def __init__(self, bot):
        self.bot=bot

    def memberscheck(self):
        def predicate(self,ctx):
            pass
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
    async def members(self, ctx, *, term=None):
        """Shows members for a given role (or all)"""
        if not term:
            return await self.users(ctx)
        role=find(lambda r: r.name.lower() == term.lower(), ctx.guild.roles)
        if not role:
            role=find(lambda r: r.name.lower().startswith(term.lower()), ctx.guild.roles)
        if not role:
            role=find(lambda r: term.lower() in r.name.lower(), ctx.guild.roles)
        if not role:
            return await ctx.send("I could not find that role.")
        if len(role.members) > 35 or len(role.members) == 0:
            return await ctx.send("There are %s members with the role "% len(role.members) + role.name.replace("@everyone","@" + '\uFEFF' + "everyone"))
        description=""
        for member in role.members:
            description=description + member.mention
        embed=discord.Embed(title=role.name,colour=0xf5a6b9)
        embed.add_field(name="Members:", value=description, inline=False)
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
        description=""
        for member in role.members:
            description=description + member.mention
        embed=discord.Embed(title="Current mutes")
        embed.add_field(name="Members:", value=description, inline=False)
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

    @commands.command(name="serverinfo",aliases=["si","server"],disabled=True)
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def serverinfo(self,ctx):
        """Shows info about a server"""
        g = ctx.guild

        embed=discord.Embed(colour=self.bot.colour)
        embed.set_author(name=f"{g.name} [{g.shard_id}]",icon_url=g.icon_url_as(static_format="png"))

        cd = g.created_at
        ge = str(g.explicit_content_filter)
        om = len(list(m for m in g.members if m.status == discord.Status.online))
        im = len(list(m for m in g.members if m.status == discord.Status.idle))
        dm = len(list(m for m in g.members if m.status == discord.Status.dnd))
        im = len(list(m for m in g.members if m.status == discord.Status.offline))
        admins = list(m for m in g.members if m.guild_permissions.administrator and not m.bot)
        mods = list(m for m in g.members if m.guild_permissions.manage_messages and not m.bot and m not in admins)
        adminbots = list(m for m in g.members if m.guild_permissions.administrator and m.bot)

        embed.add_field(inline=True,name="**Info**",value=f"**Created** {cd.year:04}/{cd.month}/{cd.day:02}\n**Region** {g.region}\n**Emojis** {len(g.emojis)}/{g.emoji_limit*2}\n**Upload Limit** {round(g.filesize_limit * 0.00000095367432)}MB\n**Verification level** {str(g.verification_level).capitalize()}\n**Media filtering** {'No one' if ge == 'Disabled' else 'No role' if ge =='no_role' else 'Everyone'}")
        embed.add_field(inline=True,name="**Members**",value=f"**All** {g.member_count}\n<:bonline:707359046122078249> {om}\n<:bidle:707359045971083315> {im}\n<:bdnd:707368559759720498> {dm}\n<:boffline:707359046138855550> {im}")
        embed.add_field(inline=True,name="**Staff**",value=f"**Owner** {g.get_member(g.owner_id).mention}\n**Admins** {len(admins)}\n**Mods** {len(mods)}\n**Admin Bots** {len(adminbots)}")

        m = await ctx.send(embed=embed)

        if (await self.bot.session.head(f"https://disboard.org/server/{g.id}")).status == 200:
            disboard = f"[Disboard](https://disboard.org/server/{g.id})"
        else:
            disboard = None

        if (await self.bot.session.head(f"https://top.gg/servers/{g.id}")).status == 200:
            topgg = f"[Top.gg](https://top.gg/servers/{g.id})"
        else:
            topgg = None
        botmemberankpos=blink.ordinal(sorted(self.bot.guilds,key=lambda x:x.member_count,reverse=True).index(g) + 1)
        nl = '\n'
        embed.add_field(name='**Other**',value=f"""
        **Unlocked Features** : {' | '.join(m.replace('_',' ').lower().capitalize() for m in (f for f in g.features if f != "MORE_EMOJI"))}
        **Boosts** {g.premium_subscription_count} | **Boosters** {len(g.premium_subscribers)}
        **Channels** {len(g.channels)} ({len(list(c for c in g.channels if isinstance(c,discord.TextChannel)))} Text, {len(list(c for c in g.channels if isinstance(c,discord.VoiceChannel)))} Voice, {len(list(c for c in g.channels if isinstance(c,discord.CategoryChannel)))} Category){(nl +'**Bans** ' + str(len(await g.bans()))) if g.me.guild_permissions.ban_members else ""}
        **Moderation requires 2FA** {'Yes' if g.mfa_level == 1 else 'No'}
        {disboard if disboard else ""} {topgg if topgg else ""}
        """,inline=False)
        embed.set_footer(text=f"{self.bot.user.name}'s {'' if botmemberankpos == '1st' else botmemberankpos} largest server")
        return await m.edit(embed=embed)


def setup(bot):
    bot.add_cog(Server(bot))
