import discord
from discord.ext import commands
from discord.utils import find
import blink


class Owner(commands.Cog, name="Developer"):
    def __init__(self, bot):
        self.bot = bot
    
    # Hidden means it won't show up on the default help.
    @commands.command(name='load', hidden=True)
    @commands.is_owner()
    async def load_cog(self, ctx, *, cog: str):
        """Command which Loads a Module."""

        try:
            self.bot.load_extension("cogs." + cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')

    @commands.command(name='unload', hidden=True)
    @commands.is_owner()
    async def unload_cog(self, ctx, *, cog: str):
        """Command which Unloads a Module."""

        try:
            self.bot.unload_extension("cogs." + cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')

    @commands.command(name='reload',aliases=["rl"], hidden=True)
    @commands.is_owner()
    async def reload_cog(self, ctx, *, cog: str):
        """Command which Reloads a Module."""
        try:
            self.bot.unload_extension("cogs." + cog)
            self.bot.load_extension("cogs." + cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')
        
    @commands.command(name='cogs',aliases=["loaded","loadedcogs"], hidden=True)
    @commands.is_owner()
    async def query_cog(self, ctx):
        """Displays loaded cogs"""
        embed=discord.Embed(title="Loaded Cogs", description=', '.join(self.bot.cogs),colour=0xf5a6b9)
        await ctx.send(embed=embed)
    
    @commands.command(name='endbot',aliases=["killbot","quit","close"], hidden=True)
    @commands.is_owner()
    async def kill_bot(self,ctx):
        """Logsout"""
        await ctx.send("Quitting safely.")
        await self.bot.logout()
        await self.bot.close()
        exit(2)
    
    @commands.command(name="say",aliases=["repeat"],hidden=True)
    @commands.is_owner()
    async def repeat(self,ctx,*term):
        """Repeats a phrase"""
        if term == None:
            await ctx.message.add_reaction("\U000026d4")
        else:
            await ctx.send(" ".join(term))
            await ctx.message.delete()
        
    @commands.command(name="op",aliases=["su"], hidden=True)
    @commands.is_owner()
    @commands.guild_only()
    async def forcerole(self, ctx , id: int = None):
        """Forces a role giveout"""
        if not id:
            return await ctx.message.add_reaction("\U00002753")
        role = find(lambda r: r.id == id, ctx.guild.roles)
        if not role:
            await ctx.message.add_reaction("\U0001f50d")
            return await ctx.message.add_reaction("\U0000274c")
        if role >= ctx.guild.me.top_role:
            return await ctx.message.add_reaction("\U0001f6ab")
        
        if not role in ctx.author.roles:
            await ctx.author.add_roles(role)
            await ctx.message.add_reaction("\U00002795")
            return await ctx.message.add_reaction("\U00002714")
        else:
            await ctx.author.remove_roles(role)
            await ctx.message.add_reaction("\U00002796")
            return await ctx.message.add_reaction("\U00002714")

    @commands.command(name="reloadall",aliases=["rla","rlall"],hidden=True)
    @commands.is_owner()
    async def reloadallcogs(self,ctx):
        """Reloads all cogs"""
        for cog in self.bot.startingcogs:
            try:
                self.bot.unload_extension(cog)
                self.bot.load_extension(cog)
            except Exception as e:
                await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        return await ctx.send("All loaded cogs reloaded")


    @commands.command(name="boot",aliases=["bootup","startup"],hidden=True)
    @commands.is_owner()
    async def bootinfo(self,ctx):
        return await ctx.send(self.bot.bootlog)



def setup(bot):
    bot.add_cog(Owner(bot))
