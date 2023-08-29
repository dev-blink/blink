# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


import time
import discord
from discord.ext import commands, menus, tasks
import asyncio
from gcloud.aio.storage import Storage
import datetime
from io import BytesIO
import aiohttp
import uuid
from jishaku.paginators import PaginatorEmbedInterface
import config
import hashlib
import blink


class AvPages(menus.ListPageSource):
    """Paginator for scrolling through avatar embeds"""
    def __init__(self, data, embeds):
        self.embeds = embeds # List of embeds to go through
        self.data = data
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        return self.embeds[entries]


class GlobalLogs(blink.Cog, name="Global logging"):
    """Logging commands"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot.logActions = 0 # statistics logging
        self.size = 512 # avatar size to push to cdn
        self.msgcache = {}
        self.voice_active = {} # (user id, server id) -> unmuted since
        self.voice_cache = {} # (user id, server id) -> activity seconds
        if not self.bot.beta:
            self.active = True # only log on production
        else:
            self.active = False

    async def init(self):  # Async init things
        self.session = aiohttp.ClientSession()
        if not self.bot.beta: # beta does not need to log!
            self.storage = Storage(
                service_file='./creds.json')
        self.blacklist = self.bot.cache_or_create( # Might aswell create a cache
            "blacklist-logging", "SELECT snowflakes FROM blacklist WHERE scope=$1",
            ("logging",)
        )
        self.batch_db_commit.start()
        await self.bot.add_cog(self)

    def cog_unload(self):
        self.batch_db_commit.cancel() # CANCEL TASK !
        self.bot.loop.create_task(self.session.close())
        super().cog_unload() # clear up client session

    # AVATAR DB TRANSACTIONS
    @commands.Cog.listener("on_user_update")
    async def update(self, before, after):
        # checks
        if not self.active:
            return
        if before.bot:
            return

        async with self.blacklist:
            if before.id in self.blacklist.value["snowflakes"]: # check blacklists
                return

        # create unique hash of the event
        uuid = f"{before}|{after}--{before.avatar}|{after.avatar}"
        transaction = str(hashlib.md5(uuid.encode()).hexdigest())

        try:
            if await self.bot.cluster.dedupe("logging", transaction): # check has for duplicate event
                return
        except asyncio.TimeoutError:
            return await self.bot.warn(f"Timeout waiting for dedupe ({uuid})", False)
        # if we are first to get this event

        self.bot.logActions += 1

        tt = datetime.datetime.utcnow().timestamp() # current timestamp
        uid = before.id # userid

        # before and after avatars
        beforeav = str(before.display_avatar.replace(static_format="jpg", size=self.size))
        afterav = str(after.display_avatar.replace(static_format="jpg", size=self.size))

        # original data base query
        result = await self.bot.DB.fetchrow("SELECT name, avatar FROM userlog WHERE id = $1", uid)

        # if we are not in the database we create a new user
        if str(result) == "SELECT 0" or result is None:
            await self._newuser(uid, str(before), beforeav, tt)
            tt = datetime.datetime.utcnow().timestamp()
            # need to change timestamp so new data not same as original

        # if usernames are different
        if str(before) != str(after): # str(discord.User) returns qualified username
            await self._update_un(uid, str(after), tt) # update username

        # if avatars are different
        if str(before.display_avatar.key) != str(after.display_avatar.key):
            await self._update_av(uid, afterav, tt) # update avatar

    def _format(self, timestamp: float, string: str):#
        """Format for database"""
        return f"{timestamp}:{string}" # database format of timestamp:entry

    def _unformat(self, query) -> tuple:
        """Unformat database entry into timestamp and entry"""
        query = query.split(":", 1)
        time = datetime.datetime.utcfromtimestamp(float(query[0]))
        return time, query[1]

    async def _newuser(self, id, oldname, oldav, timestamp):
        """Create a new database entry"""
        name = [self._format(timestamp, oldname)]
        # oldav = await self._avurl(oldav, id) # create permanent avatar url
        avatar = [] # user assets are flushed on deletion now :(
        # userlog format (id:bigint PRIMARY KEY, name:text ARRAY, avatar:text ARRAY)
        await self.bot.DB.execute("INSERT INTO userlog VALUES ($1,$2,$3)", id, name, avatar) # insert both lists

    async def _update_un(self, id, after, tt):
        """Insert an updated username into the database"""
        query = await self.bot.DB.fetch("SELECT name FROM userlog WHERE id = $1", id)
        try:
            previousNames = query[0]["name"]
        except IndexError:
            previousNames = [] # names from entry
        previousNames.append(self._format(tt, after)) # append formatted
        # update db
        await self.bot.DB.execute("UPDATE userlog SET name = $1 WHERE id = $2", previousNames, id)

    async def _update_av(self, id, after, tt):
        """Insert an updated avatar into the database"""
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
        """Upload an expiring url to the cdn"""
        if url.lower().startswith("https://cdn.discordapp.com/embed/avatars"):
            return url # these links dont expire
        try:
            r = await self.session.get(url) # download
            img_data = BytesIO(await r.read()) # put to buffer
        except Exception:
            self.session = aiohttp.ClientSession() # try again if fail
            r = await self.session.get(url)
            img_data = BytesIO(await r.read())
            # we shouldnt try more than twice

        if not r.content_length or r.content_length < 256:
            return await self.bot.warn(f"Failed to fetch image ({r.status}) {url}", False)
        path = f"avs/{id}/{uuid.uuid4()}.jpg"
        await self.storage.upload(config.cdn, path, img_data) # upload to cloud
        return f"https://{config.cdn}/{path}" # format url

    # GLOBAL MESSAGES DB TRANSACTIONS
    @commands.Cog.listener("on_message")
    async def update_db(self, message):
        if message.author.bot or not message.guild or not self.active:
            return
        async with self.blacklist:
            if message.author.id in self.blacklist.value["snowflakes"]:
                return
        # increment msg cache for user
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

        uid = user.id # user id

        # initial fetch
        result = await self.bot.DB.fetchrow("SELECT name FROM userlog WHERE id = $1", uid)

        if not result or result["name"] is None:
            return await ctx.send("No names tracked.")

        result = result["name"]
        # format array of names
        names = []
        for entry in result:
            unformatted = self._unformat(entry) # unformat into name and timestamp
            dt = unformatted[0]
            name = unformatted[1]
            names.append(
                f"{dt.day}/{dt.month}/{dt.year} @ {str(dt.hour).zfill(2)}:{str(dt.minute).zfill(2)} -> {name}"
            ) # format string
        paginator = commands.Paginator( # makes a paginator out of text that is too long
            prefix='```',
            suffix='```',
            max_size=500
        ) # ``` needed to wrap codeblock in discord
        for line in reversed(names):
            paginator.add_line(line) # each line reversed for chronological order
        embed = discord.Embed(
            colour=self.bot.colour,
            title=f"Usernames for {user}"
        )

        interface = PaginatorEmbedInterface( # create embed formatted paginator
            self.bot,
            paginator,
            owner=ctx.author,
            embed=embed,
            timeout=60
        )
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
        uid = user.id # user id

        # initial fetch
        result = await self.bot.DB.fetchrow("SELECT avatar FROM userlog WHERE id = $1", uid)

        if not result or result["avatar"] is None or len(result["avatar"]) == 0:
            return await ctx.send("No avatars tracked.")
        result = result["avatar"]
        # sort on datetime incase of timestamps being out of order
        result = sorted(result, key=lambda x: float(x.split(":", 1)[0]), reverse=True)

        # format embeds, each embed is an avatar
        embeds = []
        for entry in result:
            unformatted = self._unformat(entry)
            dt = unformatted[0]
            avatar = unformatted[1]
            embed = discord.Embed( # create embed
                description=f"[Link]({avatar})",
                colour=self.bot.colour,
                timestamp=dt
            )
            embed.set_image(url=avatar) # set image to avatar link
            embed.set_footer(text=f"{result.index(entry)+1}/{len(result)}") # positional index
            embeds.append(embed)
        if len(embeds) == 1: # cant paginate 1 embed
            return await ctx.send(embed=embeds[0])
        pages = menus.MenuPages(
            source=AvPages(
                range(0, len(embeds)),
                embeds
            ),
            clear_reactions_after=True
        )
        await pages.start(ctx) # send to ctx

    # GLOBAL MESSAGES
    @commands.command(name="messages", aliases=["msgs"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def view_messages(self, ctx):
        """Show tracked messages sent globally"""
        member = ctx.author

        async with self.blacklist:
            if ctx.author.id in self.blacklist.value["snowflakes"]:
                return await ctx.send("This service is unavailable to you")

        count = await self.bot.DB.fetchrow("SELECT * FROM globalmsg WHERE id=$1", member.id)
        if not count:
            return await ctx.send("Nothing in our database.")
        # embed formatting
        embed = discord.Embed(
            description=f'{count["messages"]} global messages sent.',
            colour=self.bot.colour
        )
        embed.set_author(name=f"{member}", icon_url=member.display_avatar.replace(static_format="png"))
        return await ctx.send(embed=embed)

    async def batch_message(self):
        if self.msgcache:
            return
        # need to create a copy because it can be changed during iteration which is bad !
        cache = dict(self.msgcache)
        self.msgcache = {}
        # iterate over and increment database
        for user in cache:
            count = cache[user]
            result = await self.bot.DB.fetchrow("SELECT * FROM globalmsg WHERE id=$1", user)
            if not result:
                await self.bot.DB.execute("INSERT INTO globalmsg VALUES ($1,$2)", user, count)
            else:
                await self.bot.DB.execute("UPDATE globalmsg SET messages=messages+$1 WHERE id=$2", count, user)

    @tasks.loop(seconds=300) # update database every 300s
    async def batch_db_commit(self):
        try:
            await self.batch_message()
        except Exception as e:
            await self.bot.warn(f"Exception in message cache, ({type(e)}) {e}", False)

        try:
            await self.batch_voice()
        except Exception as e:
            await self.bot.warn(f"Exception in voice cache, ({type(e)}) {e}", False)

    async def batch_voice(self):
        # copy pasted message cache update
        # guild id is a primary key and guilds can only be on one
        # shard so the data race condition of writing 2 at a time is avoided
        if self.voice_cache == {}:
            return
        cache = dict(self.voice_cache)
        self.voice_cache = {}
        for ((user_id, guild_id), active_time) in cache.items():

            seconds_active = int(active_time)
            result = await self.bot.DB.fetchrow("SELECT * FROM voice_activity WHERE user_id=$1 AND server_id=$2", user_id, guild_id)
            if not result:
                await self.bot.DB.execute("INSERT INTO voice_activity VALUES ($1,$2,$3)", user_id, guild_id, seconds_active)
            else:
                await self.bot.DB.execute("UPDATE voice_activity SET seconds_active=seconds_active+$1 WHERE user_id=$2 AND server_id=$3", result["seconds_active"] + seconds_active, user_id, guild_id)

    # Voice activity
    @commands.Cog.listener("on_voice_state_update")
    async def voice_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        async with self.blacklist:
            if member.id in self.blacklist.value["snowflakes"]: # check blacklists
                return

        b_muted = before.mute or before.self_mute
        a_muted = after.mute or after.self_mute

        # user disconnected
        if before.channel and not after.channel:
            self.register_voice_update(member, False)

        # user muted
        if not b_muted and a_muted:
            self.register_voice_update(member, False)

        # user joins
        if not before.channel and not a_muted and after.channel:
            self.register_voice_update(member, True)

        # user unmuted
        if b_muted and not a_muted and after.channel:
            self.register_voice_update(member, True)

    def register_voice_update(self, member:discord.Member, active: bool):

        key = (member.id, member.guild.id)

        if active:
            # already state registered
            if self.voice_active.get(key):
                return
            else:
                self.voice_active[key] = time.monotonic()

        else:
            # no state so ignore (we lose data here tho)
            if not self.voice_active.get(key):
                return
            else:
                dur = time.monotonic() - self.voice_active[key]
                self.voice_cache[key] = (self.voice_cache.get(key) or 0 + dur)
                del self.voice_active[key]

    def compute_current_additional(self, user_id, guild_id):
        # any current progress
        current = self.voice_active.get((user_id, guild_id))
        if current:
            # compute current time
            current_progress = int(time.monotonic() - current)
        else:
            current_progress = 0

        cache = self.voice_cache.get((user_id, guild_id))
        if cache:
            return int(cache) + current_progress
        else:
            return current_progress

    @commands.command(name="vc", aliaes=["vctime", "voicetime"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def voice_time(self, ctx, member: discord.Member=None):
        """Shows the amount of time spent in vc in this server"""
        if not member:
            member = ctx.author

        async with self.blacklist:
            if ctx.author.id in self.blacklist.value["snowflakes"]:
                return await ctx.send("This service is unavailable to you")

        result = await self.bot.DB.fetchrow("SELECT * FROM voice_activity WHERE user_id=$1 AND server_id=$2", member.id, member.guild.id)

        if not result:
            return await ctx.send("No data stored for this server")

        seconds_active = result['seconds_active'] + self.compute_current_additional(member.id, member.guild.id)

        embed = discord.Embed(description=f"{blink.prettydelta(seconds_active)} spent in vc.", colour=self.bot.colour)
        embed.set_author(icon_url=member.display_avatar.replace(static_format="png"), name=member.display_name)

        return await ctx.send(embed=embed)

    @commands.command(name="vctop", aliases=["vclb", "voicetop", "voiceleaderboard"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def vctop(self, ctx: blink.Ctx):
        """Shows the leaderboard for the current server"""
        async with self.blacklist:
            if ctx.author.id in self.blacklist.value["snowflakes"]:
                return await ctx.send("This service is unavailable to you")

        result = await self.bot.DB.fetch("SELECT * FROM voice_activity WHERE server_id=$2 LIMIT 10", ctx.guild.id)

        res = sorted([(r['user_id'], r['seconds_active']) for r in result], key=lambda e: e[1], reverse=True)

        embed = discord.Embed(
            description='\n'.join((f"{ctx.guild.get_member(u) or u} - {blink.prettydelta(sec)}" for u, sec in res)),
            colour=self.bot.colour
        )
        icon = (ctx.guild.icon or self.bot.user.avatar).replace(static_format="png")
        embed.set_author(author=f"Vc leaderboard for {ctx.guild.name}", icon_url=icon)

        await ctx.send(embed=embed)


async def setup(bot):
    cog = GlobalLogs(bot, "logging")
    await cog.init()
