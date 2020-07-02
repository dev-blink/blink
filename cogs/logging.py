import discord
from discord.ext import commands,menus
import asyncio
import datetime
from io import BytesIO
import random
import blink
import aiohttp


class AvPages(menus.ListPageSource):
    def __init__(self,data,embeds):
        self.embeds = embeds
        self.data = data
        super().__init__(data,per_page=1)

    async def format_page(self,menu,entries):
        return self.embeds[entries]


class GlobalLogs(commands.Cog,name="Global logging"):
    def __init__(self,bot):
        self.bot = bot
        self.active = True
        ids = blink.Config.avatar_ids()
        self.avatar_channels = []
        for id in ids:
            self.avatar_channels.append(bot.get_channel(id))

    async def init(self): # Async init things
        self.session = aiohttp.ClientSession()
        self.bot.add_cog(self)

    def __unload(self):
        asyncio.create_task(self.session.close())

# AVATAR DB TRANSACTIONS
    @commands.Cog.listener("on_user_update")
    async def update(self,before,after):
        if not self.active:
            return
        if before.bot:
            return
        tt = datetime.datetime.utcnow().timestamp()
        uid = before.id
        beforeav = str(before.avatar_url_as(format="png", size=4096))
        afterav = str(after.avatar_url_as(format="png", size=4096))
        result = await self.bot.DB.fetchrow("SELECT name, avatar FROM userlog WHERE id = $1",uid)
        if str(result) == "SELECT 0" or result is None:
            await self._newuser(uid,str(before),beforeav,tt)

        if str(before) != str(after):
            await self._update_un(uid,str(after),tt)

        if str(before.avatar_url) != str(after.avatar_url):
            await self._update_av(uid,afterav,tt)

    def avs(self):
        return random.choice(self.avatar_channels)

    def _format(self,timestamp:float,string:str):
        return f"{timestamp}:{string}"

    def _unformat(self,query) -> tuple:
        query = query.split(":",1)
        time = datetime.datetime.utcfromtimestamp(float(query[0]))
        return time, query[1]

    async def _newuser(self,id,oldname,oldav,timestamp):
        name = self._format(timestamp,oldname)
        oldav = await self._avurl(oldav)
        avatar = self._format(timestamp,oldav)
        await self.bot.DB.execute("INSERT INTO userlog VALUES ($1,$2,$3)",id,[name],[avatar]) # userlog format (id:bigint PRIMARY KEY, name:text ARRAY, avatar:text ARRAY)

    async def _update_un(self,id,after,tt):
        query = await self.bot.DB.fetch("SELECT * FROM userlog WHERE id = $1",id)
        try:
            previousNames=query[0]["name"]
        except IndexError:
            previousNames = []
        previousNames.append(self._format(tt,after))
        await self.bot.DB.execute("UPDATE userlog SET name = $1 WHERE id = $2",previousNames,id)

    async def _update_av(self,id,after,tt):
        query = await self.bot.DB.fetch("SELECT * FROM userlog WHERE id = $1",id)
        av = await self._avurl(after)
        try:
            previousAvatars=query[0]["avatar"]
        except IndexError:
            previousAvatars = []
        previousAvatars.append(self._format(tt,av))
        await self.bot.DB.execute("UPDATE userlog SET avatar = $1 WHERE id = $2",previousAvatars,id)

    async def _avurl(self,url,isretry=False):
        r = await self.session.get(str(url))
        img_data = BytesIO(await r.read())
        f = discord.File(fp=img_data, filename="av.png")
        try:
            m = await self.avs().send(file=f)
        except Exception:
            if not isretry:
                return await self._avurl(url,True)
            else:
                await self.bot.warn(f"Failed to upload url twice {url}")
                raise
        url = m.attachments[0].url
        return url

# GLOBAL MESSAGES DB TRANSACTIONS
    @commands.Cog.listener("on_message")
    async def update_db(self,message):
        if message.author.bot or not message.guild:
            return
        result=await self.bot.DB.fetchrow("SELECT * FROM globalmsg WHERE id=$1",message.author.id)
        if not result:
            await self.bot.DB.execute("INSERT INTO globalmsg VALUES ($1,$2)",message.author.id,1)
        else:
            await self.bot.DB.execute("UPDATE globalmsg SET messages=$1 WHERE id=$2",result["messages"] + 1,message.author.id)
        return

# USERNAME AND AVATAR
    @commands.command(name="names",aliases=["usernames","un"])
    @commands.bot_has_guild_permissions(send_messages=True,embed_links=True)
    async def namehistory(self,ctx,user:discord.Member=None):
        """Show username history"""
        if not user:
            user = ctx.author
        uid = user.id
        result = await self.bot.DB.fetchrow("SELECT name FROM userlog WHERE id = $1",uid)
        if not result or result["name"] is None:
            return await ctx.send("No names tracked.")
        result = result["name"]
        names=[]
        for entry in result:
            unformatted = self._unformat(entry)
            dt = unformatted[0]
            name = unformatted[1]
            names.append(f"{dt.day}/{dt.month}/{dt.year} @ {int(dt.hour):2}:{int(dt.minute):2} -> {name}")
        e = "\n".join(names)
        await ctx.send(f'```{e}```')

    @commands.command(name="avatars",aliases=["avs"])
    @commands.bot_has_guild_permissions(send_messages=True,embed_links=True,add_reactions=True)
    @commands.cooldown(1,10,commands.BucketType.user)
    async def avatarhistory(self,ctx,user:discord.Member=None):
        """Show avatar history"""
        if not user:
            user = ctx.author
        uid = user.id
        result = await self.bot.DB.fetchrow("SELECT avatar FROM userlog WHERE id = $1",uid)
        if not result or result["avatar"] is None:
            return await ctx.send("No avatars tracked.")
        result = result["avatar"]
        embeds=[]
        for entry in result:
            unformatted = self._unformat(entry)
            dt = unformatted[0]
            avatar = unformatted[1]
            timestamp = f"{dt.day}/{dt.month}/{dt.year} @ {dt.hour:02}:{dt.minute:02}"
            embed = discord.Embed(title=timestamp,description=f"[Link]({avatar})",colour=self.bot.colour)
            embed.set_image(url=avatar)
            embeds.append(embed)
        embeds.reverse()
        if len(embeds) == 1:
            return await ctx.send(embed=embeds[0])
        pages = menus.MenuPages(source=AvPages(range(1,len(embeds)), embeds), clear_reactions_after=True)
        await pages.start(ctx)

# GLOBAL MESSAGES
    @commands.command(name="messages",aliases=["msgs"])
    async def view_messages(self,ctx,member:discord.Member=None):
        """Show tracked messages sent globally"""
        if not member:
            member=ctx.author
        count=await self.bot.DB.fetchrow("SELECT * FROM globalmsg WHERE id=$1",member.id)
        if not count:
            return await ctx.send("Nothing in our database.")
        embed=discord.Embed(description=f'{count["messages"]} messages sent.',colour=self.bot.colour)
        embed.set_author(name=f"{member}",icon_url=member.avatar_url_as(static_format="png"))
        return await ctx.send(embed=embed)


def setup(bot):
    cog = GlobalLogs(bot)
    asyncio.create_task(cog.init())
