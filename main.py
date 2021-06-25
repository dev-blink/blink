# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


# External
import discord
from discord.ext import commands
import asyncpg
import aiohttp
import humanize


# Library
import datetime
import logging
import asyncio
import time
import os
import sys
import traceback
import platform


# Custom
import blink
import clusters
import config
import secrets


# logging
def loggingSetup(cluster):
    if not os.path.exists("logs"):
        os.mkdir("logs")
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG if config.beta else logging.INFO)
    handler = logging.FileHandler(
        filename=f'logs/{cluster}.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)
    return logger


def log(msg: str, scope: str):
    global printscope
    if scope == printscope:
        joiner = ""
    else:
        joiner = "\n"
        printscope = scope
    print(f"{joiner}[{scope.upper()}] {msg}")


def setupenv():
    global printscope
    printscope = ""

    # Environment
    os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
    os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
    os.environ["JISHAKU_HIDE"] = "True"
    os.environ["JISHAKU_RETAIN"] = "True"

    # Event loop
    if platform.platform().startswith("Windows"):
        log("Using Windows Selector loop", "loop")
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.set_event_loop(asyncio.SelectorEventLoop())


class Blink(commands.AutoShardedBot):
    def __init__(self, cluster: clusters.Cluster, logger: logging.Logger):

        # Clustering
        self.cluster = cluster
        shards = self.cluster.shards

        # Sharding
        self._init_shards = set()
        self._shard_ids = shards["this"]

        # Main
        super().__init__(
            command_prefix=self.get_prefix,
            help_command=None,
            shard_count=shards["total"],
            shard_ids=shards["this"],
            case_insensitive=True,
            status=discord.Status.dnd,
            activity=discord.Streaming(
                name='starting up...',
                url='https://www.twitch.tv/#'
            ),
            owner_ids=[
                171197717559771136,
                741225148509847642,
            ],
            allowed_mentions=discord.AllowedMentions(
                roles=False,
                everyone=False,
                users=False
            ),
            intents=discord.Intents(
                guilds=True,
                voice_states=True,
                guild_messages=True,
                guild_reactions=True,
                presences=config.beta,
                members=True,
            ),
            chunk_guilds_at_startup=not config.beta,
            guild_ready_timeout=10,
            max_messages=5000,
        )

        # Globals
        self._initialized = False
        self.beta = config.beta
        self.boottime = datetime.datetime.utcnow()
        self.created = False
        self.logger = logger

        # Cogs
        self._cogs = blink.CogStorage()
        self.load_extension("cogs.pre-error")
        self.loadexceptions = ""
        self.startingcogs = [
            "cogs.help",
            "cogs.member",
            "cogs.dev",
            "cogs.info",
            "cogs.error",
            "cogs.mod",
            "cogs.server",
            "cogs.fun",
            "cogs.roles",
            "cogs.advancedinfo",
            "cogs.media",
            "cogs.listing",
            "cogs.sql",
            "cogs.social"
        ]
        self.startingcogs.append("jishaku")
        if not self.beta:
            self.startingcogs.append("cogs.logging")
            self.startingcogs.append("cogs.stats")

        # Global channel cooldown
        self._cooldown = commands.CooldownMapping.from_cooldown(
            5, 5.5, commands.BucketType.channel)
        log(f"Starting - {self.cluster}", "boot")

    def __repr__(self):
        return f"<Blink bot, cluster={repr(self.cluster)}, initialized={self._initialized}, since={self.boottime}>"

    def _trace(self):
        return {
            "prod": self.__class__.__qualname__,
            "beta": self.beta,
            "cluster": self.cluster.identifier,
            "config": {
                "gateway": config.gateway,
                "cdn": config.cdn,
                "api": config.api,
                "db": config.db,
            },
            "master": {
                "total": self.cluster.ws._total_clusters,
                "sharding": {
                    "cluster": self.cluster.ws._per_cluster,
                    "total": self.cluster.ws._total_shards,
                }

            }
        }

    @property
    def colour(self):
        return 0xf5a6b9

    @property
    def default_prefixes(self):
        return [";", "b;", "B;", "blink"]

    def dispatch(self, event, *args, **kwargs):
        if self._initialized or "ready" in event:
            super().dispatch(event, *args, **kwargs)

    async def before_identify_hook(self, shard_id, *, initial=False):
        await asyncio.sleep(5)

    async def launch_shards(self):
        gateway = await self.http.get_gateway()

        self._connection.shard_count = self.shard_count
        self._connection.shard_ids = self.shard_ids

        if not self.cluster.identifier == "A":
            await self.cluster.wait_cluster()
        for shard_id in self.shard_ids:
            await self.launch_shard(gateway, shard_id, initial=(shard_id == self.shard_ids[0]))

        await self.cluster.ws.post_identify()
        self._connection.shards_launched.set()

    async def on_ready(self):
        if self._initialized:
            return
        self._initialized = True
        while len(self._init_shards) != len(self._shard_ids):
            await asyncio.sleep(1)
        await self.create()

    async def on_shard_ready(self, id):
        log(f"Shard {id} ready", "ready")
        self._init_shards.add(id)

    async def on_shard_resume(self, id):
        if self._initialized:
            await self.change_presence(shard_id=id, status=discord.Status.online, activity=discord.Streaming(name=f'b;help blinkbot.me [{self.cluster.identifier}{id}]', url='https://www.twitch.tv/#'))

    async def on_message(self, message: discord.Message):
        if not self.created:
            return
        if message.author.bot:
            return

        # blacklists
        async with self.cache_or_create("blacklist-global", "SELECT snowflakes FROM blacklist WHERE scope=$1", ("global",)) as blacklist:
            if message.author.id in blacklist.value["snowflakes"]:
                return

        # create context
        ctx = await self.get_context(message, cls=blink.Ctx)
        if not ctx.valid:
            return

        # channel ratelimit
        bucket = self._cooldown.get_bucket(message)
        if not message.channel.permissions_for(message.author).manage_messages:
            if bucket.update_rate_limit():
                if message.guild and not message.channel.permissions_for(message.guild.me):
                    pass
                try:
                    await message.add_reaction("<:CHANNEL_COOLDOWN:785184949723594782>")
                except discord.HTTPException:
                    pass
                return

        # create guild
        if ctx.guild:
            data = self.cache_or_create(
                f"guild-{ctx.guild.id}", "SELECT data FROM guilds WHERE id=$1", (ctx.guild.id,))
            async with data:
                if not data.exists:
                    await self.DB.execute("INSERT INTO guilds VALUES ($1, $2)", ctx.guild.id, "{}")
                    await data.bot_invalidate(self)
            ctx.cache = data

        await self.invoke(ctx)

    def load_extensions(self):
        for extension in self.startingcogs:
            try:
                self.load_extension(extension)
            except Exception as e:
                log(f"Unable to load: {extension} Exception was raised: {e}", "boot")
                self.loadexceptions += f"Unable to load: {extension} Exception was raised: {e}\n"

    async def invalidate_cache(self, scope: str, from_remote=False):
        local = self._cache.get(scope)
        if local:
            local.invalidate()
        if not from_remote:
            await self.cluster.dispatch({"event": "INVALIDATE_CACHE", "cache": scope})

    def cache_or_create(self, identifier: str, statement: str, values: tuple):
        if identifier.startswith("guild"):
            cls = blink.ServerCache
        else:
            cls = blink.DBCache

        if identifier in self._cache:
            return self._cache[identifier]
        cache = cls(self.DB, identifier, statement, values)
        self._cache[identifier] = cache
        return cache

    async def warn(self, message, shouldRaise=True):
        time = datetime.datetime.utcnow()
        message = f"{time.year}/{time.month}/{time.day} {time.hour}:{time.minute} [{self.cluster.identifier}/WARNING] {message}"
        await self.cluster.log_warns(message)
        if shouldRaise:
            raise blink.SilentWarning(message)

    async def create(self):
        before = time.perf_counter()
        self.cluster._post.set()

        log("Waiting on clusters", "boot")

        await self.cluster.wait_until_ready()

        log(f"Clusters took {humanize.naturaldelta(time.perf_counter()-before,minimum_unit='microseconds')} to start", "boot")

        # DB
        self.DB = await asyncpg.create_pool(**{"user": "blink", "password": secrets.db, "database": "main", "host": config.db})
        self._cache = blink.CacheDict(1024)
        self.cache_or_create(
            "blacklist-global", "SELECT snowflakes FROM blacklist WHERE scope=$1", ("global",))

        # Misc
        self.session = aiohttp.ClientSession()
        boottime = datetime.datetime.utcnow() - self.boottime

        # Extensions
        self.unload_extension("cogs.pre-error")
        self.load_extensions()

        # Bootlog
        members = sum(1 for _ in self.get_all_members())
        boot = [
            '-' * 79,
            f"**BOT STARTUP:** {self.cluster.identifier} started at {datetime.datetime.utcnow()}",
            f"```STARTUP COMPLETED IN : {boottime} ({round(members / boottime.total_seconds(),2)} members / second)",
            f"GUILDS:{len(self.guilds)}",
            f"SHARDS:{len(self.shards)}```",
        ]
        if not self.loadexceptions == "":
            boot.append("@everyone ***BOOT ERRORS***\n" + self.loadexceptions)

        self.bootlog = "\n".join(boot)
        if not self.beta:
            await self.cluster.log_startup(self.bootlog)

        # Created
        self.created = True

        log(f"Created in {humanize.naturaldelta(time.perf_counter()-before,minimum_unit='microseconds')}", "boot")
        log(f"This cluster start time was {humanize.naturaldelta(datetime.datetime.utcnow()- self.boottime)}", "boot")

        for id in self.shards:
            await self.change_presence(shard_id=id, status=discord.Status.online, activity=discord.Streaming(name=f'b;help blinkbot.me [{self.cluster.identifier}{id}]', url='https://www.twitch.tv/#'))

    async def get_prefix(self, message):

        if self.beta:
            return ["beta;"]

        async with self.cache_or_create(f"guild-{message.guild.id}", "SELECT data FROM guilds WHERE id=$1", (message.guild.id,)) as cache:
            if cache.value:
                prefixes = cache.value.get("prefixes") or self.default_prefixes
            else:
                prefixes = self.default_prefixes

        whitespace_prefixes = []

        for prefix in prefixes:
            whitespace_prefixes.append(prefix + " ")

        prefixes = whitespace_prefixes + prefixes

        return commands.when_mentioned_or(*prefixes)(self, message)

    async def cluster_event(self, payload):
        if payload is None:
            return
        if payload["event"] == "SHUTDOWN":
            await self.cluster.quit()
            await self.logout()
            await self.close()
            await self.loop.close()
            sys.exit(0)
        if payload["event"] == "RELOAD":
            self.reload_extension(payload["cog"])

        if payload["event"] == "INVALIDATE_CACHE":
            await self.invalidate_cache(payload.get("cache"), True)

    async def on_error(self, event_method, *_, **__):
        exc = sys.exc_info()
        tb = traceback.format_exc()
        embed = discord.Embed(colour=discord.Colour.red(),
                              title=f"{exc[0].__qualname__} - {exc[1]}")
        embed.set_author(name=f"Exception in event {event_method}")
        async with aiohttp.ClientSession() as cs:
            async with cs.post("https://api.github.com/gists", headers={"Authorization": "token " + secrets.gist}, json={"public": False, "files": {"traceback.txt": {"content": tb}}}) as gist:
                data = await gist.json()
                embed.description = data["html_url"]
            hook = discord.Webhook(
                secrets.errorhook, adapter=discord.AsyncWebhookAdapter(cs))
            await hook.send(embed=embed, username=f"CLUSTER {self.cluster.identifier} EVENT ERROR")


async def launch(loop):
    cluster = clusters.Cluster(config.gateway)
    cluster.start(loop)
    identifier = await cluster.wait_identifier()
    log = loggingSetup(identifier)
    bot = Blink(cluster, log)
    cluster.reg_bot(bot)
    try:
        await bot.start(secrets.token, bot=True, reconnect=True)
    except KeyboardInterrupt:
        await bot.logout()
        await cluster.quit()
        loop.close()
        sys.exit(1)
    except Exception as e:
        await cluster.crash(e, traceback.format_exc())
        print("Fatal client exception - exiting")
        await asyncio.sleep(5)
        await cluster.quit()
        loop.close()
        sys.exit(130)


if __name__ == "__main__":
    setupenv()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(launch(loop))
