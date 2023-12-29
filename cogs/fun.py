# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <blink@aaix.dev>, 29 Dec 2023


import asyncio
import discord
from discord.ext import commands
from collections import deque
import blink
import pyfiglet
import datetime
import random
from http import HTTPStatus

HTTP_CODES = list(HTTPStatus)


class Fun(blink.Cog, name="Fun"):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.snipes = {}
        self.esnipes = {}

    @commands.Cog.listener("on_message_delete")
    async def append_snipes(self, message):
        """Append snipes to queue"""

        # checks
        if len(message.content) > 1024:
            return
        if message.author.bot:
            return
        if not message.content or not message.guild:
            return
        if len(message.content) == 1:
            return

        # create 2dict if not exists
        g = self.snipes.get(message.guild.id)
        if g is None:
            g = {}
            self.snipes[message.guild.id] = {}
        snipes = g.get(message.channel.id)

        # create or add to queue
        if not snipes:
            snipes = deque([], 5)
        snipes.appendleft((message.content, str(
            message.author), discord.utils.utcnow()))
        self.snipes[message.guild.id][message.channel.id] = snipes

    @commands.command(name="clearsnipes", aliases=["cs"])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True)
    async def clear_snipes(self, ctx):
        """Clear all snipes for this guild"""
        if self.snipes.get(ctx.guild.id):
            del self.snipes[ctx.guild.id]
        if self.snipes.get(ctx.guild.id):
            del self.esnipes[ctx.guild.id]
        await ctx.send("Cleared all guild snipes")

    @commands.command(name="snipe", aliases=["s"])
    @commands.guild_only()
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    async def snipe(self, ctx):
        """Snipe recently deleted messages"""
        # check for snipes
        g = self.snipes.get(ctx.guild.id)
        if g is None:
            return await ctx.send("No snipes found.")
        snipes = g.get(ctx.channel.id)
        if snipes is None:
            return await ctx.send("No snipes found")
        # create embed
        embed = discord.Embed(title="Deleted messages", colour=self.bot.colour)
        for snipe in list(reversed(snipes)):
            embed.add_field(
                name=f"**{snipe[1]} deleted {blink.prettydelta((discord.utils.utcnow() - snipe[2]).total_seconds())} ago**", value=snipe[0], inline=False)
        return await ctx.send(embed=embed)

    @commands.Cog.listener("on_message_edit")
    async def append_edit_snipes(self, before, after):
        # checks
        if (len(before.content) + len(after.content)) > 1000:
            return
        if before.author.bot:
            return
        if not before.content or not after.content:
            return
        if before.content == after.content:
            return
        if not before.guild:
            return
        # create 2d dict
        g = self.esnipes.get(before.guild.id)
        if g is None:
            g = {}
            self.esnipes[before.guild.id] = {}
        snipes = g.get(before.channel.id)
        # add to or create queue
        if not snipes:
            snipes = deque([], 5)
        snipes.appendleft((f"{before.content} **🠢** {after.content}",
                          str(before.author), discord.utils.utcnow()))
        self.esnipes[before.guild.id][before.channel.id] = snipes

    @commands.command(name="esnipe", aliases=["editsnipe", "es"])
    @commands.guild_only()
    @commands.bot_has_guild_permissions(send_messages=True, embed_links=True)
    async def edit_snipe(self, ctx):
        """Snipe recently edited messages"""
        # check for snipes
        g = self.esnipes.get(ctx.guild.id)
        if g is None:
            return await ctx.send("No snipes found.")
        snipes = g.get(ctx.channel.id)
        if snipes is None:
            return await ctx.send("No snipes found")
        # form embed
        embed = discord.Embed(title="Edited messages", colour=self.bot.colour)
        for snipe in list(reversed(snipes)):
            embed.add_field(
                name=f"**{snipe[1]} edited {blink.prettydelta((discord.utils.utcnow() - snipe[2]).total_seconds())} ago**", value=snipe[0], inline=False)
        return await ctx.send(embed=embed)

    @commands.command(name="random")
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def rand(self, ctx, *, term=None):
        """Prints a random member of a role (if none specified @everyone)"""
        # find role
        if not term:
            role = ctx.guild.default_role
        else:
            role = await blink.searchrole(ctx.guild.roles, term)
        if not role:
            return await ctx.send("I could not find that role.")

        member = random.choice(role.members)
        # form embed
        embed = discord.Embed(title="Random member with role " + role.name,
                             description=str(member), colour=0xf5a6b9)
        embed.set_author(name=str(ctx.author),
                         icon_url=ctx.author.display_avatar.replace(static_format='png'))
        embed.set_footer(text="Chance : 1/" + str(len(role.members)))
        return await ctx.send(embed=embed)

    @commands.command(name="8ball", aliases=["roll8ball", "eightball"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def _8ball(self, ctx, *, question: str = None):
        """Shakes an 8ball"""
        responses = ['● It is certain.', '● It is decidedly so.', '● Without a doubt.', '● Yes - definitely.', '● You may rely on it.', '● As I see it, yes.', '● Most likely.', '● Outlook good.', '● Yes.', '● Signs point to yes.', '● Reply hazy, try again.',
                     '● Ask again later.', '● Better not tell you now.', '● Cannot predict now.', '● Concentrate and ask again.', "● Don't count on it.", '● My reply is no.', '● My sources say no.', '● Outlook not so good.', '● Very doubtful.']
        response = random.choice(responses).replace("●", "\U0001f3b1")
        if question: # add question mark
            if not question.endswith("?"):
                question = question + "?"
            embed = discord.Embed(
                title="\U0001f3b1 8Ball shook!", colour=self.bot.colour)
            embed.add_field(
                name='\uFEFF', value=f"Question: {question}\n***{response}***")
        else:
            embed = discord.Embed(title="\U0001f3b1 8Ball shook!",
                                  description=f"***{response}***", colour=self.bot.colour)
        await ctx.send(embed=embed)

    @commands.command(name="shipname")
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True)
    async def ship(self, ctx, member1: discord.Member, member2: discord.Member = None):
        """Creates a ship name between 2 members"""
        if not member2:
            member2 = ctx.author
        # random splice between member1:member2 and member2:member1
        # takes half of each
        choices = [f"{member1.display_name[:len(member1.display_name)//2]}{member2.display_name[len(member2.display_name)//2:]}",
                   f"{member2.display_name[:len(member2.display_name)//2]}{member1.display_name[len(member1.display_name)//2:]}"]
        await ctx.send(f"Together {member1.mention} and {member2.mention} are: **{random.choice(choices)}**!")

    @commands.command(name="pp", aliases=["penis"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def dick_size(self, ctx, *, member: discord.Member = None):
        if not member:
            member = ctx.author
        return await ctx.send(embed=discord.Embed(title=f"{member}'s size", description=f"8{'=' * blink.prand(0.7393904771901263,member.id,1,20)}D", colour=self.bot.colour))

    @commands.command(name="bigtext", aliases=["big"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(send_messages=True)
    async def bigtext(self, ctx, *, text):
        """Convert something into big text"""
        text = pyfiglet.Figlet('slant').renderText(text)
        # render text with library
        if text == "":
            return await ctx.send("No/invalid characters.")
        if len(text) > 1990:
            return await ctx.send("Output too large.")
        await ctx.send(f"```{text}```")

    @commands.command(name="thot", aliases=["thotrate", "howthot"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def thotrate(self, ctx, *, member: discord.Member = None):
        if not member:
            member = ctx.author
        return await ctx.send(embed=discord.Embed(title=f"{member}'s thotiness", description=f"{blink.prand(0.7413340535366182,member.id,0,100)}%", colour=self.bot.colour))

    @commands.command(name="gay", aliases=["gayrate", "howgay"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def gayrate(self, ctx, *, member: discord.Member = None):
        if not member:
            member = ctx.author
        return await ctx.send(embed=discord.Embed(title=f"{member}'s gayness", description=f"{blink.prand(0.8526821782827291,member.id,0,100,True)}%", colour=self.bot.colour))

    @commands.command(name="nonce", aliases=["noncerate", "hownonce"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def noncerate(self, ctx, *, member: discord.Member = None):
        if not member:
            member = ctx.author
        em = discord.Embed(title=f"{member}'s nonciness",
                           description=f"{blink.prand(0.8500969427926083,member.id,0,100,True)}%", colour=self.bot.colour)
        if blink.prand(0.8500969427926083, member.id, 0, 100, True) == 100:
            em.set_image(url="https://i.imgur.com/N9Ilqtc.png")
        return await ctx.send(embed=em)

    @commands.command(name="mock")
    @commands.bot_has_permissions(send_messages=True)
    async def mock(self, ctx, *, text: str = None):
        """Mock some text"""
        await ctx.send("".join(random.choice([c.upper, c.lower])() for c in text or "mock what!??!"))

    @commands.command(name="countdown")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def countdown(self, ctx):
        return await ctx.send("no countdown active")

    @commands.command(name="nuke", hidden=True)
    @commands.bot_has_permissions(send_messages=True)
    async def nuke(self, ctx): # joke command
        await ctx.send("nuking <a:bloading:705202826946674718>")

    @commands.command(name="poll")
    @commands.bot_has_permissions(send_messages=True, embed_links=True, add_reactions=True)
    async def poll(self, ctx: blink.Ctx, *, question: str=None):
        """Start a reaction poll"""

        # insane indenting..
        if question is None:
            ref = ctx.message.reference
            if ref and ref.cached_message:
                question = ref.cached_message.content

        if question is None:
            question = "?"
        embed = discord.Embed(
            title="Poll",
            description=question + ("?" if not question.endswith("?") else ""),
            colour=self.bot.colour
        )
        msg = await ctx.send(embed=embed)
        await asyncio.gather(msg.add_reaction("✅"), msg.add_reaction("❎"))

    @commands.command(name="http", aliases=["httpcat",])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def httpcat(self, ctx: blink.Ctx, code:int=None):
        if code is None:
            code = random.choice(HTTP_CODES)
        return await ctx.send(f"https://http.cat/{code}")


async def setup(bot):
    await bot.add_cog(Fun(bot, "fun"))
