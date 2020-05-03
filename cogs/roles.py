import discord
from discord.ext import commands
import blink


class RoleManagement(commands.Cog,name="Role Management"):
    def __init__(self,bot):
        self.bot=bot

    @commands.command(name="role",aliases=["changerole","setrole"])
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_roles=True)
    async def role(self, ctx,user: discord.Member=None, *,term):
        """Changes roles for a user."""
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("I do not have permission to manage roles.")
        if term == "everyone":
            return
        if not user:
            return await ctx.send("I am unable to find that user.")
        role=await blink.searchrole(ctx.guild.roles,term)
        if not role:
            return await ctx.send("I could not find that role.")

        if not ctx.author == ctx.guild.owner:
            if role >= ctx.author.top_role:
                return await ctx.send("You are unable to give that role. (Check your role position.)")
        if role >= ctx.guild.me.top_role:
            return await ctx.send("I am unable to assign that role. (Check my role position.)")
        if role in user.roles:
            await user.remove_roles(role, reason=(ctx.author.name + "#" + str(ctx.author.discriminator)),atomic=True)
            return await ctx.send("Removed role **`%s`** from "% role.name + user.mention)
        else:
            await user.add_roles(role, reason=(ctx.author.name + "#" + str(ctx.author.discriminator)),atomic=True)
            return await ctx.send("Added role **`%s`** to "% role.name + user.mention)

    @commands.command(name='roles',aliases=["showroles"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def showroles(self, ctx, *, member: discord.Member=None):
        """Shows a members roles."""

        if not member:
            member=ctx.author

        roles=""
        for role in member.roles:
            if len(member.roles) == 1:
                roles="No roles"
            else:
                roles=roles +(role.name + "\n")

        embed=discord.Embed(colour=self.bot.colour)
        embed.set_author(icon_url=member.avatar_url_as(static_format='png'), name=str(member))

        # \uFEFF is a Zero-Width Space
        embed.add_field(name=f"Roles for {member.name}#{member.discriminator} in {ctx.guild.name}", value=roles)

        await ctx.send(embed=embed)

    @commands.command(name="createrole",aliases=["newrole","+role","role+","addrole"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def addrole(self,ctx,*rolename):
        """Creates a new role"""
        if not rolename:
            return await ctx.send("You must specify a role name.")
        try:
            await ctx.guild.create_role(name=" ".join(rolename), permissions=discord.Permissions.none(),reason=f"Created by {ctx.author.name}#{ctx.author.discriminator}")
            return await ctx.send(f"Successfully created the role: " +" ".join(rolename))
        except Exception as e:
            print(e)
            return await ctx.send("I am unable to create that role.")

    @commands.command(name="rolecolour",aliases=["rolecolor"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True,manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def rolecolour(self,ctx,term=None,colour: discord.Colour=None):
        """Sets a role colour from a hex code."""
        if not term:
            return await ctx.send("Please specify a role.")
        if not colour:
            return await ctx.send("Please specify a colour.")
        role=await blink.searchrole(ctx.guild.roles,term)
        if not role:
            return await ctx.send("I could not find that role.")
        if not ctx.author == ctx.guild.owner:
            if role >= ctx.author.top_role:
                return await ctx.send("You are unable to modify that role. (Check your role position.)")
        if role >= ctx.guild.me.top_role:
            return await ctx.send("I am unable to modify that role. (Check my role position.)")
        await role.edit(colour=colour,reason=f"{ctx.author} updated the colour to {colour}.")
        return await ctx.send(f"Updated {role.name} to {colour}")


def setup(bot):
    bot.add_cog(RoleManagement(bot))
