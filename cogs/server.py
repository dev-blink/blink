import discord
from discord.ext import commands
from discord.utils import find
import blink

class Server(commands.Cog,name="Server"):
    def __init__(self, bot):
        self.bot = bot
    @commands.command(name="members")
    @commands.guild_only()
    async def members(self, ctx, *, term=None):
        """Shows members for a given role (or all)"""
        if not term:
            return await Server.users(self,ctx)
        if not ctx.author.guild_permissions.manage_roles:
            return await ctx.send(f'you do not have permission to use the command **`{ctx.command}`** in that way.')
        role = find(lambda r: r.name.lower() == term.lower(), ctx.guild.roles)
        if not role:
            role = find(lambda r: r.name.lower().startswith(term.lower()), ctx.guild.roles)
        if not role:
            role = find(lambda r: term.lower() in r.name.lower(), ctx.guild.roles)
        if not role:
            return await ctx.send("I could not find that role.")
        
        if len(role.members) > 20 or len(role.members) == 0:
            return await ctx.send("There are %s members with the role "%len(role.members) + role.name)
        description = ""
        for member in role.members:
            description = description + member.mention
        embed=discord.Embed(title=role.name,colour=0xf5a6b9)
        embed.add_field(name="Members:", value=description, inline=False)
        await ctx.send(embed=embed)
    

    @commands.command(name="muted",aliases=["mutes","currentmutes"])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def muted(self, ctx):
        """Shows currently muted members"""
        role = await blink.searchrole(ctx.guild.roles,"muted")
        if not role:
            return await ctx.send("I could not find the muted.")
        if len(role.members) == 0:
            return await ctx.send("There are no currently muted members.")
        description = ""
        for member in role.members:
            description = description + member.mention
        embed=discord.Embed(title="Current mutes")
        embed.add_field(name="Members:", value=description, inline=False)
        await ctx.send(embed=embed)
        

    @commands.command(name="users",aliases=["membercount"])
    @commands.guild_only()
    async def users(self,ctx):
        """Shows the user count for the guild."""
        embed=discord.Embed(title=(ctx.guild.name + ":"),colour=self.bot.colour)
        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.add_field(name="Guild Members:", value=ctx.guild.member_count, inline=False)
        return await ctx.send(embed=embed)


    @commands.command(name="lock")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def lockchannel(self,ctx,channel:discord.TextChannel = None):
        """Locks a channel."""
        if not channel:
            channel = ctx.channel
        await channel.set_permissions(ctx.guild.default_role, overwrite=discord.PermissionOverwrite(send_messages=False))
        await ctx.send(f"Locked {channel.name} for all members.")


    @commands.command(name="unlock")
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def unlocklockchannel(self,ctx,channel:discord.TextChannel = None):
        """Unlocks a channel."""
        if not channel:
            channel = ctx.channel
        await channel.set_permissions(ctx.guild.default_role, overwrite=discord.PermissionOverwrite(send_messages=True))
        await ctx.send(f"Unlocked {channel.name} for all members.")

        
        
        
        



def setup(bot):
    bot.add_cog(Server(bot))