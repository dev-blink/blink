# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


import asyncio
import discord
from discord.ext import commands
import datetime
import blink


statuses = { # map of statuses to images representing them in the ui
    discord.Status.online: "https://cdn.discordapp.com/emojis/707359046122078249.png?v=1",
    discord.Status.idle: "https://cdn.discordapp.com/emojis/707359045971083315.png?v=1",
    discord.Status.dnd: "https://cdn.discordapp.com/emojis/707368559759720498.png?v=1",
    discord.Status.offline: "https://cdn.discordapp.com/emojis/707359046138855550.png?v=1",
}
flags = { # map of user flags to emojis
    discord.UserFlags.bug_hunter: "<:bughunter:747172876624593007>",
    discord.UserFlags.bug_hunter_level_2: "<:bughunter2:747166557204906055>",

    discord.UserFlags.staff: "<:staff:747166866127978518>",
    discord.UserFlags.system: "<:system1:747173687882416128><:system2:747173765149884467>",
    discord.UserFlags.partner: "<:partner:747174087201128498>",

    discord.UserFlags.verified_bot_developer: "<:earlydev:747166557129539586>",
    discord.UserFlags.verified_bot: "<:bot1:747181929844965437><:bot2:747181965018529862>",

    discord.UserFlags.early_supporter: "<:earlysupporter:747168624313237515>",

    discord.UserFlags.hypesquad: "<:hypesquad:747166557678862439>",
    discord.UserFlags.hypesquad_balance: "<:balance:747166557137797133>",
    discord.UserFlags.hypesquad_bravery: "<:bravery:747166557326803074>",
    discord.UserFlags.hypesquad_brilliance: "<:brilliance:747166557083402371>",
}


async def convert(seconds):
    """Nicely display spotify duration"""
    delta = str(datetime.timedelta(seconds=seconds))
    if delta[:3] == "0:0":
        return delta[3:]
    elif delta[:2] == "0:":
        return delta[2:]
    else:
        return delta


class Members(blink.Cog, name="Member"):
    async def guild_av(self, m):
        member = await self.bot.http.get_member(m.guild.id, m.id)
        # fetch the raw member for guild avatar because not in library k
        av_hash = member.get("avatar")
        if av_hash:
            return f"https://cdn.discordapp.com/guilds/{m.guild.id}/users/{m.id}/avatars/{av_hash}.png?size=1024"

    def avatar_embed(self, link):
        """Form an avatar embed from a link"""
        embed = discord.Embed(colour=self.bot.colour)
        embed.set_author(name="Link", url=link)
        embed.set_image(url=link)
        embed.set_footer(text="Press ↔️ to change to avatar")
        return embed

    @commands.command(name="joined", aliases=["joinedat", "joindate"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True)
    async def joined(self, ctx, *, member: discord.Member):
        """Show when a member joined."""
        await ctx.send(f'{member.display_name} joined at {member.joined_at} UTC')

    @commands.command(name='toprole', aliases=['top_role'])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True)
    async def show_toprole(self, ctx, *, member: discord.Member = None):
        """Shows the members Top Role."""

        if member is None:
            member = ctx.author

        await ctx.send(f'The top role for {member.display_name} is `{member.top_role.name}`')

    @commands.command(name='perms', aliases=['permsfor', 'permissions'])
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def check_permissions(self, ctx, *, member: discord.Member = None):
        """Checks a members guild permissions"""

        if not member:
            member = ctx.author

        perms = '\n'.join( # iterate over perms 
            # value is a 1/0 or true/false of wether the user has that permission
            perm for perm, value in member.guild_permissions if value)

        embed = discord.Embed(
            title='Permissions for:',
            description=ctx.guild.name,
            colour=self.bot.colour
        )
        embed.set_author(
            icon_url=member.avatar_url_as(
            static_format='png'),
            name=str(member)
        )

        # \uFEFF is a zero width space
        embed.add_field(name='\uFEFF', value=perms)

        await ctx.send(content=None, embed=embed)

    @commands.command(name="whois", aliases=["userinfo", "who", "ui"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def whois(self, ctx, *, member: discord.Member = None):
        """Shows various info about a user"""
        if not member:
            member: discord.Member = ctx.author

        embed = discord.Embed( # add badges from public flags using emoji dict
            description=' '.join(flags[f] for f in member.public_flags.all()),
            colour=self.bot.colour
        )
        embed.set_author( # set author badge to status icon image
            name=f"{member}",
            url=member.avatar_url_as(static_format='png'),
            icon_url=statuses[member.status]
        )
        # thumbnail to user avatar
        embed.set_thumbnail(url=member.avatar_url_as(static_format='png'))

        # guild join date
        j = member.joined_at
        joindate = f"{j.day}/{j.month}/{j.year} {j.hour}:{j.minute:02}"
        embed.add_field(name="User joined:", value=joindate, inline=True)

        # created at datae
        r = member.created_at
        registerdate = f"{r.day}/{r.month}/{r.year} {r.hour}:{r.minute:02}"
        embed.add_field(
            name="User registered:",
            value=registerdate,
            inline=True
        )

        # join position
        sortedmembers = sorted(
            ctx.guild.members,
            key=lambda member: member.joined_at
        )
        joinposition = sortedmembers.index(member) + 1
        embed.add_field(name="Join position:", value=joinposition, inline=True)

        # special permission
        if member == ctx.guild.owner:
            hasadmin = "Server Owner"
        elif member.guild_permissions.administrator:
            hasadmin = "Administrator"
        elif member.guild_permissions.manage_messages:
            hasadmin = "Moderator"
        else:
            hasadmin = "Member"
        embed.add_field(name="Server Status", value=hasadmin, inline=True)

        # no of roles
        rolecount = len(member.roles) - 1
        embed.add_field(name="Number of roles:", value=rolecount, inline=True)

        # top role
        highestrole = member.top_role
        embed.add_field(name="Highest role:", value=highestrole, inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="avatar", aliases=["av", "pfp"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def av(self, ctx, *, user: discord.Member = None):
        """Shows a user's avatar"""
        if not user:
            user = ctx.author
        
        # normal user avatar embed
        global_av_embed = self.avatar_embed(user.avatar_url_as(static_format="png"))
        msg = await ctx.send(embed=global_av_embed)
        if user.bot: # bots cannot have guild avatars
            return
        await msg.add_reaction("↔️")

        guild_av = None
        guild_av_embed = None

        try:
            while True: # continuously loop through reaction add/remove to see if user pressed a button
                await self.bot.wait_for("reaction_add", check=lambda r, u: u.id == ctx.author.id and str(r.emoji) == "↔️",timeout=30)
                # check if the guild_av has been tried, and then try and fetch it
                # needs to be cached to prevent excessive http api requests
                if not guild_av:
                    guild_av = await self.guild_av(user) # try fetch guild avatar
                    if not guild_av:
                        return await msg.edit(content="No server avatar available",embed=global_av_embed)
                    else:
                        guild_av_embed = self.avatar_embed(guild_av) # create embed
                await msg.edit(embed=guild_av_embed) # swap embed

                await self.bot.wait_for("reaction_remove", check=lambda r, u: u.id == ctx.author.id and str(r.emoji) == "↔️", timeout=30)
                await msg.edit(embed=global_av_embed) # swap back
        except asyncio.TimeoutError:
            return # done waiting for user

    @commands.command(name="status")
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def status(self, ctx, *, user: discord.Member = None):
        """Shows a user's status"""
        if not user:
            user = ctx.author

        # generator of all user activities
        activities = (a for a in user.activities if not isinstance(a, discord.Spotify))

        try: # try to get first activity
            base = next(activities)
        except StopIteration:
            return await ctx.send("no non-spotify activity could be detected, use the spotify command for spotify status")

        # user has an emoji or a custom status
        if isinstance(base, discord.CustomActivity):
            if not base.name:
                base.name = "Custom Emoji:"
            embed = discord.Embed(
                title=base.name or discord.embeds.EmptyEmbed, colour=self.bot.colour)
            if base.emoji:
                embed.set_thumbnail(url=base.emoji.url)
            embed.set_author(
                name=user.name, icon_url=user.avatar_url_as(static_format='png'))

        # user is 'playing' status
        elif isinstance(base, discord.Activity):
            embed = discord.Embed(colour=self.bot.colour)
            embed.set_author(
                name=user.name, icon_url=user.avatar_url_as(static_format='png'))
            embed.add_field(name="Playing " + base.name, value=base.details or f"for {blink.prettydelta((datetime.datetime.utcnow() -  base.created_at).total_seconds())}" if base.created_at else "No timing available", inline=False)

        # user is 'streaming' on twitch
        elif isinstance(base, discord.Streaming):
            embed = discord.Embed(
                title="Streaming", url=base.url, description=base.name or base.url, colour=0x593695)
        else:
            embed = False
        
        # if an embed was generated
        if embed:
            return await ctx.send(embed=embed)
        # could not make an embed, must have no valid status
        await ctx.send("A status was unable to be determined.")

    @commands.command(name="listening", aliases=["playing", "spotify", "spot"])
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def spotifystatus(self, ctx, user: discord.Member = None):
        """Displays a members spotify status"""
        if not user:
            user = ctx.author

        # generator for list of spotify activities
        activities = (a for a in user.activities if isinstance(a, discord.Spotify))

        try: # get first activity
            spotify = next(activities)
        except StopIteration:
            return await ctx.send("no spotify detected")

        if isinstance(spotify, discord.Spotify):
            spotifyembed = discord.Embed(
                title=f"{spotify.title}", colour=spotify.colour)

            spotifyembed.add_field(
                name="Album:", value=spotify.album, inline=False)

            spotifyembed.set_thumbnail(url=spotify.album_cover_url)

            artists = ", ".join(spotify.artists)
            if len(spotify.artists) > 1:
                pluralartist = "Artists:"
            else:
                pluralartist = "By:"
            spotifyembed.add_field(
                name=pluralartist, value=artists, inline=False)

            songtime = await convert(spotify.duration.seconds)
            spotifyembed.add_field(
                name="Duration:", value=songtime, inline=False)
            return await ctx.send(embed=spotifyembed)
        
        # unreachable allows support for other methods of getting
        # spotifty data without significant refactoring


def setup(bot):
    bot.add_cog(Members(bot, "member"))
