# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <blink@aaix.dev>, 29 Dec 2023


import discord
from discord.ext import commands
import blink
from typing import Union


class RoleManagement(blink.Cog, name="Role Management"):
    @commands.command(name="role", aliases=["changerole", "setrole"])
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def role(self, ctx, user: discord.Member, *, term: Union[int, str]):
        """Changes roles for a user."""
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("I do not have permission to manage roles.")
        role = ctx.guild.get_role(term)
        if not role:
            role = await blink.searchrole(ctx.guild.roles, str(term))
        if not role:
            return await ctx.send("I could not find that role.")

        if role.is_integration():
            return await ctx.send("I am unable to assign integration roles")

        if role.is_premium_subscriber():
            return await ctx.send("I am unable to assign the booster role")

        if role.is_bot_managed():
            return await ctx.send("I am unable to assign bot owned roles")

        if role.is_default():
            return await ctx.send("Cannot assign the @everyone role", allowed_mentions=discord.AllowedMentions.none())

        if not ctx.author == ctx.guild.owner:
            if role >= ctx.author.top_role:
                return await ctx.send("You are unable to give that role. (Check your role position.)")
        if role >= ctx.guild.me.top_role:
            return await ctx.send("I am unable to assign that role. (Check my role position.)")
        if role in user.roles:
            await user.remove_roles(role, reason=str(ctx.author), atomic=True)
            return await ctx.send("Removed role **`%s`** from " % role.name + user.mention)
        else:
            await user.add_roles(role, reason=str(ctx.author), atomic=True)
            return await ctx.send("Added role **`%s`** to " % role.name + user.mention)

    @commands.command(name='roles', aliases=["showroles"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def showroles(self, ctx, *, member: discord.Member = None):
        """Shows a members roles."""

        if not member:
            member = ctx.author

        roles = ""
        for role in reversed(member.roles):
            if len(member.roles) == 1:
                roles = "No roles"
            else:
                roles = roles + (role.name + "\n")

        embed = discord.Embed(colour=self.bot.colour)
        embed.set_author(icon_url=member.display_avatar.replace(
            static_format='png'), name=str(member))
        embed.add_field(
            name=f"Roles for {member} in {ctx.guild.name}", value=roles)

        await ctx.send(embed=embed)

    @commands.command(name="createrole", aliases=["newrole", "+role", "role+", "addrole"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def addrole(self, ctx, *rolename):
        """Creates a new role"""
        if not rolename:
            return await ctx.send("You must specify a role name.")
        try:
            await ctx.guild.create_role(name=" ".join(rolename), permissions=discord.Permissions.none(), reason=f"Created by {ctx.author}")
            return await ctx.send("Successfully created the role: " + " ".join(rolename))
        except discord.DiscordException:
            return await ctx.send("I am unable to create that role.")

    @commands.command(name="rolecolour", aliases=["rolecolor"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def rolecolour(self, ctx, term: str, colour: discord.Colour):
        """Sets a role colour from a hex code."""
        role = ctx.guild.get_role(term)
        if not role:
            role = await blink.searchrole(ctx.guild.roles, term)
        if not role:
            return await ctx.send("I could not find that role.")
        if not ctx.author == ctx.guild.owner:
            if role >= ctx.author.top_role:
                return await ctx.send("You are unable to modify that role. (Check your role position.)")
        if role >= ctx.guild.me.top_role:
            return await ctx.send("I am unable to modify that role. (Check my role position.)")
        await role.edit(colour=colour, reason=f"{ctx.author} updated the colour to {colour}.")
        return await ctx.send(f"Updated {role.name} to {colour}")

    @commands.command(name="hoist", aliases=["elevate"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def hoistrole(self, ctx, *, term):
        """Display a role seperately from online members"""
        role = ctx.guild.get_role(term)
        if not role:
            role = await blink.searchrole(ctx.guild.roles, term)
        if not role:
            return await ctx.send("I could not find that role.")
        if not ctx.author == ctx.guild.owner:
            if role >= ctx.author.top_role:
                return await ctx.send("You are unable to modify that role. (Check your role position.)")
        if role >= ctx.guild.me.top_role:
            return await ctx.send("I am unable to modify that role. (Check my role position.)")
        hoisted = role.hoist
        await role.edit(hoist=not hoisted)
        await ctx.send(f"{role.name} {'has been de'if hoisted else 'is now '}hoisted.")


async def setup(bot):
    await bot.add_cog(RoleManagement(bot, "roles"))
