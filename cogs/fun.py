import discord
from discord.ext import commands
from collections import deque
import blink
import pyfiglet
import datetime
import random


class Fun(commands.Cog,name="Fun"):
    def __init__(self,bot):
        self.bot=bot
        self.snipes = {}
        self.esnipes= {}

    @commands.Cog.listener("on_message_delete")
    async def append_snipes(self,message):
        if len(message.content) > 1024 or message.author.bot or not message.content:
            return
        snipes = self.snipes.get(message.guild.id).get(message.channel.id)
        if not snipes:
            snipes = deque([],5)
        snipes.appendleft((message.content,str(message.author),datetime.datetime.utcnow()))
        self.snipes[message.guild.id][message.channel.id] = snipes

    @commands.command(name="snipe")
    @commands.guild_only()
    @commands.bot_has_guild_permissions(send_messages=True,embed_links=True)
    async def snipe(self,ctx):
        """Snipe recently deleted messages"""
        g = self.snipes.get(ctx.guild.id)
        if g is None:
            return await ctx.send("No snipes found.")
        snipes = g.get(ctx.channel.id)
        if snipes is None:
            return await ctx.send("No snipes found")
        embed=discord.Embed(title="Deleted messages",colour=self.bot.colour)
        for snipe in list(reversed(snipes)):
            embed.add_field(name=f"**{snipe[1]} deleted {blink.prettydelta((datetime.datetime.utcnow() - snipe[2]).total_seconds())} ago**",value=snipe[0],inline=False)
        return await ctx.send(embed=embed)

    @commands.Cog.listener("on_message_edit")
    async def append_edit_snipes(self,before,after):
        if (len(before.content) + len(after.content)) > 1024 or before.author.bot or not before.content:
            return
        snipes = self.esnipes.get(before.guild.id).get(before.channel.id)
        if not snipes:
            snipes = deque([],5)
        snipes.appendleft((f"{before.content} **🠢** {after.content}",str(before.author),datetime.datetime.utcnow()))
        self.esnipes[before.guild.id][before.channel.id] = snipes

    @commands.command(name="esnipe",aliases=["editsnipe"])
    @commands.guild_only()
    @commands.bot_has_guild_permissions(send_messages=True,embed_links=True)
    async def edit_snipe(self,ctx):
        g = self.esnipes.get(ctx.guild.id)
        if g is None:
            return await ctx.send("No snipes found.")
        snipes = g.get(ctx.channel.id)
        if snipes is None:
            return await ctx.send("No snipes found")
        embed=discord.Embed(title="Edited messages",colour=self.bot.colour)
        for snipe in list(reversed(snipes)):
            embed.add_field(name=f"**{snipe[1]} edited {blink.prettydelta((datetime.datetime.utcnow() - snipe[2]).total_seconds())} ago**",value=snipe[0],inline=False)
        return await ctx.send(embed=embed)

    @commands.command(name="random")
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def random(self,ctx,*,term=None):
        """Prints a random member of a role (if none specified @everyone)"""

        if not term:
            role=ctx.guild.default_role
        else:
            role=await blink.searchrole(ctx.guild.roles,term)
        if not role:
            return await ctx.send("I could not find that role.")

        rand=random.randint(1, len(role.members)) - 1
        member=role.members[rand]
        embed=discord.Embed(title="Random member with role " + role.name, description=member.mention,colour=0xf5a6b9)
        embed.set_author(name=ctx.author.name + "#" + str(ctx.author.discriminator),icon_url=ctx.author.avatar_url_as(static_format='png'))
        embed.set_footer(text="Chance : 1/" + str(len(role.members)))
        return await ctx.send(embed=embed)

    @commands.command(name="8ball",aliases=["roll8ball","eightball"])
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def _8ball(self, ctx,*,question:str=None):
        """Shakes an 8ball"""
        responses=['● It is certain.', '● It is decidedly so.', '● Without a doubt.', '● Yes - definitely.', '● You may rely on it.', '● As I see it, yes.', '● Most likely.', '● Outlook good.', '● Yes.', '● Signs point to yes.', '● Reply hazy, try again.', '● Ask again later.', '● Better not tell you now.', '● Cannot predict now.', '● Concentrate and ask again.', "● Don't count on it.", '● My reply is no.', '● My sources say no.', '● Outlook not so good.', '● Very doubtful.']
        response=responses[random.randint(1, len(responses)) - 1].replace("●","\U0001f3b1")
        if question:
            if not question.endswith("?"):
                question=question + "?"
            embed=discord.Embed(title="\U0001f3b1 8Ball shook!",colour=self.bot.colour)
            embed.add_field(name='\uFEFF',value=f"Question: {question}\n***{response}***")
        else:
            embed=discord.Embed(title="\U0001f3b1 8Ball shook!",description=f"***{response}***",colour=self.bot.colour)
        await ctx.send(embed=embed)

    @commands.command(name="ship")
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True)
    async def ship(self,ctx,member1:discord.Member=None,member2:discord.Member=None):
        """Creates a ship name between 2 members"""
        if not member1:
            return await ctx.send("Ship with who?")
        if not member2:
            member2=ctx.author
        if not member1.nick:
            member1.nick=member1.name
        if not member2.nick:
            member2.nick=member2.name
        choices=[f"{member1.nick[:len(member1.nick)//2]}{member2.nick[len(member2.nick)//2:]}",f"{member2.nick[:len(member2.nick)//2]}{member1.nick[len(member1.nick)//2:]}"]
        await ctx.send(f"Together {member1.mention} and {member2.mention} are: **{random.choice(choices)}**!")

    @commands.command(name="dong",aliases=["dicksize","penissize","penis","dick"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def dick_size(self,ctx,member:discord.Member=None):
        """Dong size..."""
        if not member:
            member=ctx.author
        return await ctx.send(embed=discord.Embed(title=f"{member}'s size",description=f"8{'=' * blink.prand(0.7393904771901263,member.id,1,20)}D",colour=self.bot.colour))

    @commands.command(name="bigtext",aliases=["big"])
    @commands.cooldown(1,5,commands.BucketType.user)
    @commands.bot_has_permissions(send_messages=True)
    async def bigtext(self,ctx,*,text:str=""):
        """Convert something into big text"""
        if len(text) > 30:
            return await ctx.send("30 characters max please...")
        text=pyfiglet.Figlet('slant').renderText(text)
        if text == "":
            return await ctx.send("No/invalid characters.")
        await ctx.send(f"```{text}```")

    @commands.command(name="thot",aliases=["thotrate","howthot"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def thotrate(self,ctx,member:discord.Member=None):
        """How thotty are you?"""
        if not member:
            member=ctx.author
        return await ctx.send(embed=discord.Embed(title=f"{member}'s thotiness",description=f"{blink.prand(0.7413340535366182,member.id,0,100)}%",colour=self.bot.colour))

    @commands.command(name="gay",aliases=["gayrate","howgay"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def gayrate(self,ctx,member:discord.Member=None):
        """How gay are you?"""
        if not member:
            member=ctx.author
        return await ctx.send(embed=discord.Embed(title=f"{member}'s gayness",description=f"{blink.prand(0.8526821782827291,member.id,0,100,True)}%",colour=self.bot.colour))

    @commands.command(name="nonce",aliases=["noncerate","hownonce"])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True,embed_links=True)
    async def noncerate(self,ctx,member:discord.Member=None):
        """How much of a nonce are you?"""
        if not member:
            member=ctx.author
        em=discord.Embed(title=f"{member}'s nonciness",description=f"{blink.prand(0.8500969427926083,member.id,0,100,True)}%",colour=self.bot.colour)
        if blink.prand(0.8500969427926083,member.id,0,100,True) == 100:
            em.set_image(url="https://i.imgur.com/N9Ilqtc.png")
        return await ctx.send(embed=em)

    @commands.command(name="mock")
    async def mock(self, ctx,*, text:str=None):
        await ctx.send("".join(random.choice([c.upper, c.lower])() for c in text or "mock what!??!"))


def setup(bot):
    bot.add_cog(Fun(bot))
