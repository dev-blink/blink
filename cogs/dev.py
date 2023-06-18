# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


import discord
from discord.ext import commands
from discord.utils import find
import objgraph
from collections import Counter
import asyncio
import blink
import uuid
import contextlib


class Owner(blink.Cog, name="Developer"):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blacklist_scopes = ["logging", "global", "transform"]

    @commands.command(name="selfpurge", hidden=True)
    @commands.is_owner()
    async def selfpurge(self, ctx, count: int = 10):
        """Purge all messages within the given history"""
        async for message in ctx.history(limit=count):
            if message.author == ctx.me:
                try:
                    await message.delete()
                except discord.errors.NotFound:
                    pass

    @commands.command(name="purgecache", hidden=True)
    @commands.is_owner()
    async def purge_cache(self, ctx, *, cache: str):
        await self.bot.invalidate_cache(cache)
        await ctx.message.add_reaction("✅")

    @commands.command(name="blacklist", hidden=True)
    @commands.is_owner()
    async def blacklist(self, ctx, scope: str, action: str):
        """Modifiy blacklists"""
        if scope not in self.blacklist_scopes:
            return await ctx.send("Invalid scope")

        async with self.bot.cache_or_create(f"blacklist-{scope}", "SELECT snowflakes FROM blacklist WHERE scope=$1", (scope,)) as cache:
            blacklist = cache.value["snowflakes"]
            if "+" in action:
                id = int(action.replace("+", ""))
                if id in blacklist:
                    return await ctx.send("Already blacklisted")
                else:
                    blacklist.append(id)
            elif "-" in action:
                id = int(action.replace("-", ""))
                try:
                    blacklist.remove(id)
                except ValueError:
                    return await ctx.send("User not in blacklist")
            else:
                return await ctx.send("invalid action (+ or -)")
            await self.bot.DB.execute("UPDATE blacklist SET snowflakes=$1 WHERE scope=$2", blacklist, scope)
            await cache.bot_invalidate(self.bot)
        return await ctx.send(action)

    @commands.command(name="delav", hidden=True)
    @commands.is_owner()
    async def rm_avatar(self, ctx, user: int, link: str):
        """Remove an avatar from a user"""
        avs = (await self.bot.DB.fetchrow("SELECT avatar FROM userlog WHERE id=$1", user))["avatar"]
        query = [av for av in avs if av.split(":", 1)[1].endswith(link)]
        if query == []:
            return await ctx.send("Not Found")
        for match in query:
            avs.pop(avs.index(match))
        res = await self.bot.DB.execute("UPDATE userlog SET avatar=$1 WHERE id=$2", avs, user)
        return await ctx.send(res)

    @commands.command(name='load', hidden=True)
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True)
    async def load_cog(self, ctx, *, cog: str):
        """Command which Loads a Module."""

        try:
            if cog in ["jsk", "jishaku"]:
                cog = "jishaku"
                await self.bot.load_extension(cog)
            else:
                await self.bot.load_extension("cogs." + cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')

    @commands.command(name='unload', hidden=True)
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True)
    async def unload_cog(self, ctx, *, cog: str):
        """Command which Unloads a Module."""
        if cog == "music":
            if not await self.musiccheck(ctx):
                return
        try:
            if cog in ["jsk", "jishaku"]:
                cog = "jishaku"
                await self.bot.unload_extension(cog)
            else:
                await self.bot.unload_extension("cogs." + cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')

    @commands.command(name='reload', aliases=["rl"], hidden=True)
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True)
    async def reload_cog(self, ctx, *, cog: str):
        """Command which Reloads a Module."""
        if cog == "music":
            if not await self.musiccheck(ctx):
                return
        try:
            if cog == "jishaku":
                await self.bot.unload_extension(cog)
                await self.bot.load_extension(cog)
            else:
                await self.bot.unload_extension("cogs." + cog)
                await self.bot.load_extension("cogs." + cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')
            await self.bot.cluster.dispatch({"event": "RELOAD", "cog": ("cogs." + cog if not cog == "jishaku" else cog)})

    @commands.command(name='cogs', aliases=["loaded", "loadedcogs"], hidden=True)
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def query_cog(self, ctx):
        """Displays loaded cogs"""
        embed = discord.Embed(
            title="Loaded Cogs",
            description='\n'.join(
                "\n".join([getattr(self.bot._cogs, c).__class__.__qualname__ for c in dir(self.bot._cogs)])
            ),
            colour=0xf5a6b9
        )
        await ctx.send(embed=embed)

    @commands.command(name='close-bot', aliases=["killbot", "closebot"], hidden=True)
    @commands.is_owner()
    async def kill_bot(self, ctx):
        """Logsout"""
        if self.bot.beta:
            await self.bot.cluster.dispatch({"event": "SHUTDOWN"})
            await ctx.send("Quitting safely.")
            await self.bot.stop()
            exit()

        if not await self.musiccheck(ctx):
            return
        check = str(uuid.uuid4())
        await self.bot.warn(f"Shutdown attempted, key is:\n{check}", False)
        await ctx.send("Please enter a key")
        try:
            await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and m.content == check, timeout=15)
        except asyncio.TimeoutError:
            return await ctx.send("Timeout achieved")
        await self.bot.cluster.dispatch({"event": "SHUTDOWN"})
        await ctx.send("Quitting safely.")
        await self.bot.stop()
        exit()

    @commands.command(name="say", hidden=True)
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True)
    async def repeat(self, ctx, *, term: str):
        """Repeats a phrase"""
        await ctx.send(term)
        with contextlib.suppress(discord.Forbidden):
            await ctx.message.delete()

    @commands.command(name="op", aliases=["su"], hidden=True)
    @commands.is_owner()
    @commands.guild_only()
    @commands.bot_has_permissions(add_reactions=True, manage_roles=True)
    async def forcerole(self, ctx, id: int = None):
        """Forces a role giveout"""
        if not id:
            return await ctx.message.add_reaction("\U00002753")
        role = find(lambda r: r.id == id, ctx.guild.roles)
        if not role:
            await ctx.message.add_reaction("\U0001f50d")
            return await ctx.message.add_reaction("\U0000274c")
        if role >= ctx.guild.me.top_role:
            return await ctx.message.add_reaction("\U0001f6ab")

        if role not in ctx.author.roles:
            await ctx.author.add_roles(role)
            await ctx.message.add_reaction("\U00002795")
            return await ctx.message.add_reaction("\U00002714")
        else:
            await ctx.author.remove_roles(role)
            await ctx.message.add_reaction("\U00002796")
            return await ctx.message.add_reaction("\U00002714")

    @commands.command(name="reloadall", aliases=["rla", "rlall"], hidden=True)
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True)
    async def reloadallcogs(self, ctx):
        """Reloads all cogs"""
        if not await self.musiccheck(ctx):
            return
        for cog in self.bot.startingcogs:
            try:
                await self.bot.unload_extension(cog)
                await self.bot.load_extension(cog)
            except Exception as e:
                await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        return await ctx.send("All loaded cogs reloaded")

    @commands.command(name="boot", aliases=["bootup", "startup"], hidden=True)
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True)
    async def bootinfo(self, ctx):
        return await ctx.send(self.bot.bootlog)

    @commands.command(name="memcheck", hidden=True)
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True)
    async def leak_checker(self, ctx):
        bot = self.bot
        typestats = objgraph.typestats(shortnames=False)

        def sanity(left, name, *, _stats=typestats):
            try:
                right = _stats[name]
            except KeyError:
                return f'{name}: {left}. Not found'
            else:
                cmp = '!=' if left != right else '=='
                return f'{name}: {left} {cmp} {right}'

        def get_all_overwrites():
            return sum(len(c._overwrites) for c in bot.get_all_channels())

        def get_all_roles():
            return sum(len(g.roles) for g in bot.guilds)

        # Cache sanity
        channels = Counter(type(c) for c in bot.get_all_channels())

        return await ctx.send(f"total-cache```{sanity(channels[discord.TextChannel], 'discord.channel.TextChannel')}\n{sanity(channels[discord.VoiceChannel], 'discord.channel.VoiceChannel')}\n{sanity(128, 'discord.channel.DMChannel')}\n{sanity(channels[discord.CategoryChannel], 'discord.channel.CategoryChannel')}\n{sanity(len(bot.guilds), 'discord.guild.Guild')}\n{sanity(5000, 'discord.message.Message')}\n{sanity(len(bot.users), 'discord.user.User')}\n{sanity(sum(1 for _ in bot.get_all_members()), 'discord.member.Member')}\n{sanity(len(bot.emojis), 'discord.emoji.Emoji')}\n{sanity(get_all_overwrites(), 'discord.abc._Overwrites')}\n{sanity(get_all_roles(), 'discord.role.Role')}```")

    async def musiccheck(self, ctx):
        """Check to not interrupt music players if music is playing before shutdown"""
        if not self.bot.cluster.music == 0:
            m = await ctx.send(f"Players would be cancelled: {self.bot.cluster.music}")
            await m.add_reaction("\U00002714")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) == '\U00002714'
            try:
                await self.bot.wait_for('reaction_add', timeout=3, check=check)
            except asyncio.TimeoutError:
                await m.add_reaction("\U0000231b")
                return False
            else:
                return True
        else:
            return True


async def setup(bot):
    await bot.add_cog(Owner(bot, "dev"))
