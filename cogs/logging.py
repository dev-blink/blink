# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


import discord
from discord.ext import commands, menus, tasks
import asyncio
import datetime
from io import BytesIO
import aiohttp
import uuid
from jishaku.paginators import PaginatorEmbedInterface
import config
import hashlib
import blink


class AvPages(menus.ListPageSource):
    def __init__(self, data, embeds):
        self.embeds = embeds # List of embeds to go through
        self.data = data
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        return self.embeds[entries]


class GlobalLogs(blink.Cog, name="Global logging"):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot.logActions = 0 # statistics logging
        self.size = 512 # avatar size to push to cdn
        self.msgcache = {}
        if not self.bot.beta:
            self.active = True # only log on production
        else:
            self.active = False

    async def init(self):  # Async init things
        self.session = aiohttp.ClientSession()
        if not self.bot.beta:
            from gcloud.aio.storage import Storage
            self.storage = Storage(
                service_file='./creds.json')
        self.blacklist = self.bot.cache_or_create(
            "blacklist-logging", "SELECT snowflakes FROM blacklist WHERE scope=$1", ("logging",))
        self.message_push.start()
        self.bot.add_cog(self)

    def cog_unload(self):
        self.message_push.cancel()
        super().cog_unload()

    # AVATAR DB TRANSACTIONS
    @commands.Cog.listener("on_user_update")
    async def update(self, before, after):
        if not self.active:
            return
        if before.bot:
            return

        async with self.blacklist:
            if before.id in self.blacklist.value["snowflakes"]:
                return
        uuid = f"{before}|{after}--{before.avatar}|{after.avatar}"
        transaction = str(hashlib.md5(uuid.encode()).hexdigest())
        try:
            if await self.bot.cluster.dedupe("logging", transaction):
                return
        except asyncio.TimeoutError:
            return await self.bot.warn(f"Timeout waiting for dedupe ({uuid})", False)
        self.bot.logActions += 1
        tt = datetime.datetime.utcnow().timestamp()
        uid = before.id
        beforeav = str(before.avatar_url_as(
            static_format="jpg", size=self.size))
        afterav = str(after.avatar_url_as(static_format="jpg", size=self.size))
        result = await self.bot.DB.fetchrow("SELECT name, avatar FROM userlog WHERE id = $1", uid)
        if str(result) == "SELECT 0" or result is None:
            await self._newuser(uid, str(before), beforeav, tt)
            tt = datetime.datetime.utcnow().timestamp()

        if str(before) != str(after):
            await self._update_un(uid, str(after), tt)

        if str(before.avatar_url) != str(after.avatar_url):
            await self._update_av(uid, afterav, tt)

    def _format(self, timestamp: float, string: str):
        return f"{timestamp}:{string}"

    def _unformat(self, query) -> tuple:
        query = query.split(":", 1)
        time = datetime.datetime.utcfromtimestamp(float(query[0]))
        return time, query[1]

    async def _newuser(self, id, oldname, oldav, timestamp):
        name = [self._format(timestamp, oldname)]
        oldav = await self._avurl(oldav, id)
        avatar = [self._format(timestamp, oldav)]
        # userlog format (id:bigint PRIMARY KEY, name:text ARRAY, avatar:text ARRAY)
        await self.bot.DB.execute("INSERT INTO userlog VALUES ($1,$2,$3)", id, name, avatar)

    async def _update_un(self, id, after, tt):
        query = await self.bot.DB.fetch("SELECT name FROM userlog WHERE id = $1", id)
        try:
            previousNames = query[0]["name"]
        except IndexError:
            previousNames = []
        previousNames.append(self._format(tt, after))
        await self.bot.DB.execute("UPDATE userlog SET name = $1 WHERE id = $2", previousNames, id)

    async def _update_av(self, id, after, tt):
        query = await self.bot.DB.fetch("SELECT avatar FROM userlog WHERE id = $1", id)
        av = await self._avurl(after, id)
        try:
            previousAvatars = query[0]["avatar"]
        except IndexError:
            previousAvatars = []
        previousAvatars.append(self._format(tt, av))

        # remove all avatars older than av_max_age because they will be purged from the cdn anyways
        now = datetime.datetime.utcnow()
        previousAvatars = [av for av in previousAvatars if (now - self._unformat(av)[0]).days < config.av_max_age]

        await self.bot.DB.execute("UPDATE userlog SET avatar = $1 WHERE id = $2", previousAvatars, id)

    async def _avurl(self, url, id):
        if url.lower().startswith("https://cdn.discordapp.com/embed/avatars"):
            return url
        try:
            r = await self.session.get(url)
            img_data = BytesIO(await r.read())
        except Exception:
            self.session = aiohttp.ClientSession()
            r = await self.session.get(url)
            img_data = BytesIO(await r.read())
        ext = str(url).replace(f"?size={self.size}", "").split(".")[-1]
        path = f"avs/{id}/{uuid.uuid4()}.{ext}"
        await self.storage.upload(config.cdn, path, img_data)
        return f"https://{config.cdn}/{path}"

    # GLOBAL MESSAGES DB TRANSACTIONS
    @commands.Cog.listener("on_message")
    async def update_db(self, message):
        if message.author.bot or not message.guild or not self.active:
            return
        async with self.blacklist:
            if message.author.id in self.blacklist.value["snowflakes"]:
                return
        user = message.author.id
        if self.msgcache.get(user) is None:
            self.msgcache[user] = 1
        else:
            self.msgcache[user] += 1

    # USERNAME AND AVATAR
    @commands.command(name="names", aliases=["usernames", "un"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True, add_reactions=True)
    async def namehistory(self, ctx, user: discord.Member = None):
        """Show username history"""
        if not user:
            user = ctx.author
        async with self.blacklist:
            if ctx.author.id in self.blacklist.value["snowflakes"]:
                return await ctx.send("This service is unavailable to you")
        uid = user.id
        result = await self.bot.DB.fetchrow("SELECT name FROM userlog WHERE id = $1", uid)
        if not result or result["name"] is None:
            return await ctx.send("No names tracked.")
        result = result["name"]
        names = []
        for entry in result:
            unformatted = self._unformat(entry)
            dt = unformatted[0]
            name = unformatted[1]
            names.append(
                f"{dt.day}/{dt.month}/{dt.year} @ {str(dt.hour).zfill(2)}:{str(dt.minute).zfill(2)} -> {name}")
        paginator = commands.Paginator(
            prefix='```', suffix='```', max_size=500)
        for line in reversed(names):
            paginator.add_line(line)
        embed = discord.Embed(colour=self.bot.colour,
                              title=f"Usernames for {user}")
        interface = PaginatorEmbedInterface(
            self.bot, paginator, owner=ctx.author, embed=embed, timeout=60)
        return await interface.send_to(ctx)

    @commands.command(name="avatars", aliases=["avs"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True, add_reactions=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def avatarhistory(self, ctx, *, user: discord.Member = None):
        """Show avatar history"""
        if not user:
            user = ctx.author
        async with self.blacklist:
            if ctx.author.id in self.blacklist.value["snowflakes"]:
                return await ctx.send("This service is unavailable to you")
        uid = user.id
        result = await self.bot.DB.fetchrow("SELECT avatar FROM userlog WHERE id = $1", uid)
        if not result or result["avatar"] is None or len(result["avatar"]) == 0:
            return await ctx.send("No avatars tracked.")
        result = result["avatar"]
        result = sorted(result, key=lambda x: float(
            x.split(":", 1)[0]), reverse=True)
        embeds = []
        for entry in result:
            unformatted = self._unformat(entry)
            dt = unformatted[0]
            avatar = unformatted[1]
            embed = discord.Embed(
                description=f"[Link]({avatar})", colour=self.bot.colour, timestamp=dt)
            embed.set_image(url=avatar)
            embed.set_footer(text=f"{result.index(entry)+1}/{len(result)}")
            embeds.append(embed)
        if len(embeds) == 1:
            return await ctx.send(embed=embeds[0])
        pages = menus.MenuPages(source=AvPages(
            range(0, len(embeds)), embeds), clear_reactions_after=True)
        await pages.start(ctx)

    # GLOBAL MESSAGES
    @commands.command(name="messages", aliases=["msgs"])
    async def view_messages(self, ctx):
        """Show tracked messages sent globally"""
        member = ctx.author
        count = await self.bot.DB.fetchrow("SELECT * FROM globalmsg WHERE id=$1", member.id)
        if not count:
            return await ctx.send("Nothing in our database.")
        embed = discord.Embed(
            description=f'{count["messages"]} messages sent.', colour=self.bot.colour)
        embed.set_author(
            name=f"{member}", icon_url=member.avatar_url_as(static_format="png"))
        return await ctx.send(embed=embed)

    async def batch(self):
        if self.msgcache == {} or self.active is False:
            return
        cache = dict(self.msgcache)
        self.msgcache = {}
        for user in cache:
            count = cache[user]
            result = await self.bot.DB.fetchrow("SELECT * FROM globalmsg WHERE id=$1", user)
            if not result:
                await self.bot.DB.execute("INSERT INTO globalmsg VALUES ($1,$2)", user, count)
            else:
                await self.bot.DB.execute("UPDATE globalmsg SET messages=$1 WHERE id=$2", result["messages"] + count, user)

    @tasks.loop(seconds=60)
    async def message_push(self):
        try:
            await self.batch()
        except Exception as e:
            await self.bot.warn(f"Exception in message cache, ({type(e)}) {e}", False)


def setup(bot):
    cog = GlobalLogs(bot, "logging")
    bot.loop.create_task(cog.init())
