import discord
from discord.ext import commands
import datetime


async def convert(seconds):
    delta=str(datetime.timedelta(seconds=seconds))
    if delta[:3] == "0:0":
        return delta[3:]
    elif delta[:2] == "0:":
        return delta[2:]
    else:
        return delta


class Members(commands.Cog,name="Member"):
    def __init__(self, bot):
        self.bot=bot

    @commands.command(name="joined",aliases=["joinedat","joindate"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True)
    async def joined(self, ctx, *, member: discord.Member):
        """Says when a member joined."""
        await ctx.send(f'{member.display_name} joined on {member.joined_at}')

    @commands.command(name='toprole', aliases=['top_role'])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True)
    async def show_toprole(self, ctx, *, member: discord.Member=None):
        """Shows the members Top Role."""

        if member is None:
            member=ctx.author

        await ctx.send(f'The top role for {member.display_name} is ```{member.top_role.name}```')

    @commands.command(name='perms', aliases=['perms_for', 'permissions'])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def check_permissions(self, ctx, *, member: discord.Member=None):
        """Checks a members guild permissions"""

        if not member:
            member=ctx.author

        perms='\n'.join(perm for perm, value in member.guild_permissions if value)

        embed=discord.Embed(title='Permissions for:', description=ctx.guild.name,colour=0xf5a6b9)
        embed.set_author(icon_url=member.avatar_url_as(static_format='png'), name=str(member))

        # \uFEFF is a Zero-Width Space
        embed.add_field(name='\uFEFF', value=perms)

        await ctx.send(content=None, embed=embed)

    @commands.command(name="whois",aliases=["userinfo","who","ui"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def whois(self, ctx, user: discord.Member=None):
        """Shows various info about a user"""
        if not user:
            user=ctx.author
        statuses = {
            "online":"<:bonline:707359046122078249>",
            "idle":"<:bidle:707359045971083315>",
            "dnd":"<:bdnd:707368559759720498>",
            "offline":"<:boffline:707359046138855550>",
        }
        member=ctx.guild.get_member(user.id)

        embed=discord.Embed(description=member.mention,colour=0xf5a6b9)
        embed.set_author(name=f"{user} {statuses[str(user.status)]}", url=user.avatar_url_as(static_format='png'),icon_url=user.avatar_url_as(static_format='png'))

        joined=member.joined_at
        joindate=str(joined.day) + "/" + str(joined.month) + "/" + str(joined.year) + "  " + str(joined.hour) + ":" + str(joined.minute).zfill(2)
        embed.add_field(name="User joined:", value=joindate, inline=True)

        registered=user.created_at
        registerdate=str(registered.day) + "/" + str(registered.month) + "/" + str(registered.year) + "  " + str(registered.hour) + ":" + str(registered.minute).zfill(2)
        embed.add_field(name="User registered:", value=registerdate, inline=True)

        sortedmembers=sorted(ctx.guild.members, key=lambda member: member.joined_at)
        joinposition=sortedmembers.index(member) + 1
        embed.add_field(name="Join position:", value=joinposition, inline=True)

        if member == ctx.guild.owner:
            hasadmin ="Server Owner"
        elif member.guild_permissions.administrator:
            hasadmin="Administrator"
        elif member.guild_permissions.manage_messages:
            hasadmin="Moderator"
        else:
            hasadmin="Member"
        embed.add_field(name="Server Status", value=hasadmin, inline=True)

        rolecount=len(member.roles) - 1
        embed.add_field(name="Number of roles:", value=rolecount, inline=True)

        highestrole=member.top_role
        embed.add_field(name="Highest role:", value=highestrole, inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="avatar",aliases=["av","pfp"])
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def av(self, ctx, user: discord.Member=None):
        """Shows a user's avatar"""
        if not user:
            user=ctx.author
        embed=discord.Embed(colour=0xf5a6b9)
        embed.set_author(name="Link", url=user.avatar_url_as(static_format='png'))
        embed.set_image(url=user.avatar_url_as(static_format='png'))
        await ctx.send(embed=embed)

    @commands.command(name="status")
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def status(self, ctx, *, user:discord.Member=None):
        """Shows a user's status"""
        if not user:
            user=ctx.author

        if len(list(user.activities)) == 2:
            base, secondary=user.activities
            if secondary:
                pass
        else:
            base=user.activity
        if not base:
            return await ctx.send("No status detected.")

        if isinstance(base, discord.CustomActivity):
            if not base.name:
                base.name="Custom Emoji:"
            embed=discord.Embed(title=base.name or discord.embeds.EmptyEmbed,colour=self.bot.colour)
            if base.emoji:
                embed.set_thumbnail(url=base.emoji.url)
            embed.set_author(name=user.name,icon_url=user.avatar_url_as(static_format='png'))

        elif isinstance(base, discord.Activity):
            embed=discord.Embed(colour=0xf5a6b9)
            embed.set_author(name=user.name,icon_url=user.avatar_url_as(static_format='png'))
            embed.add_field(name=base.name, value=base.details, inline=False)

        elif isinstance(base, discord.Streaming):
            embed=discord.Embed(title="Streaming", url=base.url,description=base.name,colour=0x593695)
        else:
            embed=False
        if embed:
            return await ctx.send(embed=embed)
        await ctx.send("A status was unable to be determined.")

    @commands.command(name="listening",aliases=["playing","spotify","spot"])
    @commands.guild_only()
    @commands.cooldown(1,10, commands.BucketType.user)
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def spotifystatus(self,ctx,user: discord.Member=None):
        """Displays a members spotify status"""
        if not user:
            user=ctx.author

        if len(list(user.activities)) == 2:
            base, secondary=user.activities
        else:
            base=user.activity
            secondary=None

        if isinstance(base, discord.Spotify):
            spotify=base
        elif isinstance(secondary, discord.Spotify):
            spotify=secondary
        else:
            return await ctx.send("No spotify detected.")

        if isinstance(spotify, discord.Spotify):
            spotifyembed=discord.Embed(title=f"{spotify.title}",colour=spotify.colour)

            spotifyembed.add_field(name="Album:",value=spotify.album,inline=False)

            spotifyembed.set_thumbnail(url=spotify.album_cover_url)

            artists=", ".join(spotify.artists)
            if len(spotify.artists) > 1:
                pluralartist="Artists:"
            else:
                pluralartist="By:"
            spotifyembed.add_field(name=pluralartist,value=artists, inline=False)

            songtime=await convert(spotify.duration.seconds)
            spotifyembed.add_field(name="Duration:",value=songtime,inline=False)
            return await ctx.send(embed=spotifyembed)


def setup(bot):
    bot.add_cog(Members(bot))
