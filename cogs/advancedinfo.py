import discord
from discord.ext import commands
import base64
import datetime
import asyncio
import blink

class AdvancedInfo(commands.Cog,name="Advanced info"):
    def __init__(self,bot):
        self.bot = bot
        self.colour = bot.colour
    
    @commands.command(name="token",aliases=["guesstoken"])
    @commands.guild_only()
    async def tokenguess(self,ctx,member:discord.Member=None):
        """Guesses a users token, with a hint of accuracy"""
        if not member:
            member = ctx.author
        p1 = base64.b64encode(str(member.id).encode("UTF-8"))
        p1 = p1.decode("UTF-8")
        p2 = "#" * 6
        p3 = "#" * 27
        out = f"Non mfa token: **`{p1}.{p2}.{p3}`**"
        return await ctx.send(out)
    

    @commands.command(name="pid",aliases=["parseid"])
    @commands.bot_has_permissions(embed_links=True,send_messages=True)
    async def parse_id(self,ctx,obj):
        """Parses a discord ID."""
        if not obj:
            id = ctx.author.id
        else:
            id = obj
            rm = ["<",">","@","&","#","!"]
            for x in rm:
                id = id.replace(x,"")
        try:
            id = int(id)
        except:
            return await ctx.send("Not a valid ID.")
        binaryid = bin(int(id))[2:]
        time = binaryid[:42]
        worker = binaryid[42:47]
        process = binaryid[47:52]
        count = binaryid[52:]
        parsedid = f"{time}-{worker}-{process}-{count}"
        embed = discord.Embed(title=id,description=parsedid,colour=self.colour)
        msg = f"```INTERNAL WORKER: {int(worker,2)}\nINTERNAL PROCESS ID: {int(process,2)}\nGENERATOR ITERATIVE: {int(count,2)}```"
        embed.add_field(name="Parsed ID",value=msg)
        embed.set_footer(text=f"CREATION DATE: {datetime.datetime.utcfromtimestamp(((id >> 22) + 1420070400000) / 1000).isoformat()}")
        return await ctx.send(embed=embed)

    @commands.command(name="lookup")
    @commands.bot_has_permissions(embed_links=True,send_messages=True)
    async def lookup_user(self,ctx,userid:int=None):
        """Looks up a user by their ID"""
        if not userid:
            return await ctx.send("Please specify a user by their ID.")
        try:
            user = await self.bot.fetch_user(userid)
        except:
            return await ctx.send("I am unable to find that user.")
        
        embed = discord.Embed(title=f"User lookup for: {userid}",description=user.mention,colour=self.colour)
        registered = user.created_at
        embed.add_field(name="Tag:",value=f"{user.name}#{user.discriminator}")
        registerdate = str(registered.day) + "/" + str(registered.month) + "/" + str(registered.year) + "  " + str(registered.hour) + ":" + str(registered.minute).zfill(2)
        embed.add_field(name="User registered:", value=registerdate, inline=True)
        return await ctx.send(embed=embed)
    
    @commands.command(name="checktoken",aliases=["tokencheck"])
    @commands.bot_has_permissions(embed_links=True,send_messages=True)
    @commands.cooldown(1,30,commands.BucketType.user)
    async def token_eval(self,ctx,token:str=None):
        """Check a bot token."""
        if not token:
            return await ctx.send("No token")
        if not __import__("re").compile(r"([a-zA-Z0-9]{24}\.[a-zA-Z0-9]{6}\.[a-zA-Z0-9_\-]{27}|mfa\.[a-zA-Z0-9_\-]{84})").match(token):
            return await ctx.send("Invalid token.")
        
        embed=discord.Embed(title="No return")

        clientinstance = discord.Client()
        @clientinstance.event
        async def on_ready():
            nonlocal embed
            if len(clientinstance.guilds) == 0:
                embed = discord.Embed(title=f"{clientinstance.user.name}#{clientinstance.user.discriminator} can see no guilds.")
                await clientinstance.logout()
                return
            largest_guild = sorted(clientinstance.guilds,key=lambda x: x.member_count,reverse=True)[0]
            embed = discord.Embed(title=f"{clientinstance.user.name}#{clientinstance.user.discriminator} bot info",description=f"```Servers: {len(clientinstance.guilds)}\nMembers: {len(list(clientinstance.get_all_members())) - 1}\nLargest server: {largest_guild.name} ({largest_guild.member_count} members)```",colour=self.bot.colour)
            if len(clientinstance.guilds) in range(2,11):
                fguilds = []
                for guild in clientinstance.guilds:
                    fguilds.append(f"{guild.name} - owned by {guild.owner.name}#{guild.owner.discriminator} with {guild.member_count} members")
                formated = "\n".join(fguilds)
                embed.add_field(name="Guilds:",value=f"```{formated}```")
            await clientinstance.logout()
            await clientinstance.close()
        await ctx.message.add_reaction("<a:loading:701617517663354910>")
        try:
            await clientinstance.start(token,bot=True)
        except:
            await clientinstance.close()
            await ctx.message.add_reaction("\U0000274c")
            await ctx.message.remove_reaction("<a:loading:701617517663354910>",ctx.guild.me)
        else:
            await ctx.message.add_reaction("\U00002714")
            await ctx.message.remove_reaction("<a:loading:701617517663354910>",ctx.guild.me)
        await ctx.send(embed=embed)
        
    


 
def setup(bot):
    bot.add_cog(AdvancedInfo(bot))
