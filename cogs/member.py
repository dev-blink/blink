# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


import asyncio
import discord
from discord.ext import commands
import datetime
import blink
import aiohttp
import blinksecrets as secrets


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lyric_cache = blink.CacheDict(10_000)
        self.dead_tracks = set()

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
            icon_url=member.avatar_url_as(static_format='png'),
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

    @commands.command(name="spotify", aliases=["lyrics", "l", "fm", "so", "sp"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def display_lyrics(self, ctx):
        """Display the lyrics if they are available"""
        sp = await self.get_spotify(ctx.author)
        lyrics = await self.get_lyrics(sp.title, sp.artists, sp.track_id)

        if not lyrics:
            # legacy embed
            embed = discord.Embed(
                title=f"{sp.title} - {', '.join(sp.artists.split('; '))}",
                colour=sp.colour
            )
            embed.add_field(
                name="Album",
                value=sp.album,
            )
            embed.set_thumbnail(
                url=sp.icon_url
            )
            return await ctx.send(embed=embed)

        delta = (datetime.datetime.utcnow() - sp.started_at).seconds

        time, index, interval, l1, l2, l3, real_index, max_index = self.lyric_index(lyrics, delta)

        pre_song = index == 1 and real_index == -1
        post_song = index == -2 and real_index == 0

        first_lyric = index - real_index == 1
        last_lyric = index == max_index

        l1, l2, l3 = (k['lyrics'].strip().replace("*","\\*") for k in (l1, l2, l3))

        display = [
            f"**{l1}**" if first_lyric else l1,
            f"**{l2}**" if not (first_lyric or last_lyric or pre_song or post_song) else l2,
            f"**{l3}**" if last_lyric else l3,
        ]

        if pre_song:
            display.pop()
            display.insert(0, "♫♫♫")
        elif post_song:
            del display[0]
            display.append("♫♫♫")

        embed = discord.Embed(
            title=f"{sp.title} - {', '.join(sp.artists.split('; '))}",
            description="\n".join(display),
            colour=sp.colour,
        )
        embed.set_thumbnail(url=sp.icon_url)
        await ctx.send(
            # content=f"{time=} {index=} {interval=} {real_index=}\n{pre_song=} {post_song=} {first_lyric=} {last_lyric=}",
            embed=embed
        )

    def get_current_pos_str(self, start, end, display_len):
        current_duration = datetime.datetime.utcnow() - start
        total_duration = end - start
        current_pos = current_duration / total_duration
        return current_pos

    async def get_lyrics(self, track, artists, track_id):
        if self.lyric_cache.get(track_id):
            return self.lyric_cache[track_id]
        if track_id in self.dead_tracks:
            return None

        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://api.textyl.co/api/lyrics?q={track} - {artists}") as req:
                try:
                    data = await req.json()
                except aiohttp.ContentTypeError:
                    self.dead_tracks.add(track_id)
                    return None

        self.lyric_cache[track_id] = data
        return data

    def lyric_index(self, data: list, time: int):
        index = -2
        real_index = 0
        max_index = len(data) - 1
        for (i, lyric) in enumerate(data):
            if lyric['seconds'] >= time:
                index = i - 1
                real_index = i - 1
                break
        if index in (-1, 0):
            index = 1
        interval = data[index + 1]['seconds'] - time
        return time, index, interval, data[index - 1], data[index], data[index + 1], real_index, max_index

    @commands.command(name="spotifysync")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def spotify_url(self, ctx):
        """Sync spotify to blink"""
        await ctx.send("This command is currently waiting for spotify to authorize blink bot before it will work.")
        state = await self.get_state(ctx.author.id)
        url = f"https://accounts.spotify.com/authorize?client_id=4dc7aefcb3674ee2864123eddcdadd4e&state={state}&redirect_uri=https://callback.blinkbot.me&response_type=code&scope=user-read-currently-playing"
        embed = discord.Embed(
            title="Click to authorize blink bot to view your spotify activity",
            url=url,
            colour=self.bot.colour
        )
        try:
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            return await ctx.send("Please enable dms")
        await ctx.send("A link has been sent to your dm to authorize, this link expires in 5 minutes, do not share it with anyone")

    async def get_state(self, user_id):
        async with aiohttp.ClientSession() as cs:
            async with cs.get(
                f"https://sp.blinkbot.me/state/{user_id}",
                headers={
                    "Authorization": secrets.spotify_api
                }
            ) as res:
                payload = await res.json()
                return payload['state']

    async def get_spotify_from_worker(self, user_id):
        async with aiohttp.ClientSession() as cs:
            async with cs.get(
                f"https://sp.blinkbot.me/current/{user_id}",
                headers={
                    "Authorization": secrets.spotify_api
                }
            ) as res:
                try:
                    payload = await res.json()
                except aiohttp.ContentTypeError:
                    payload = {}
                return payload, res.status

    async def get_spotify(self, member: discord.Member):
        try:
            sp = next(p for p in member.activities if isinstance(p, discord.Spotify))
        except StopIteration:
            sp, status = await self.get_spotify_from_worker(member.id)
            if status != 200:
                raise blink.SpotifyApiResponseError(status)

        return blink.SpotifyData(sp)


def setup(bot):
    bot.add_cog(Members(bot, "member"))
