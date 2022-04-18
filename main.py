# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


# External
from typing import Dict, List, Union
import discord
from discord.ext import commands, tasks
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
import blinksecrets as secrets


# logging
def loggingSetup(cluster) -> logging.Logger:
    """Creates a log file named after the cluster given"""
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
    """Separate print statements by what category of information they are (scope)"""
    global printscope
    if scope == printscope:
        joiner = ""
    else:
        joiner = "\n"
        printscope = scope
    print(f"{joiner}[{scope.upper()}] {msg}")


def setupenv():
    """Set environment variables and change event loop on windows"""
    global printscope
    printscope = ""

    # Environment
    os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
    os.environ["JISHAKU_NO_DM_TRACEBACK"] = str(not config.beta)
    os.environ["JISHAKU_HIDE"] = "True"
    os.environ["JISHAKU_RETAIN"] = "True"

    # Event loop
    if platform.platform().startswith("Windows"):
        log("Using Windows Selector loop", "loop")
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.set_event_loop(asyncio.SelectorEventLoop())


class Blink(commands.AutoShardedBot):
    """Main bot class for blink bot"""

    def __init__(self, cluster: clusters.Cluster, logger: logging.Logger):

        # Clustering
        self.cluster: clusters.Cluster = cluster
        shards = self.cluster.shards

        # Sharding
        self._init_shards: set(int) = set()
        self._shard_ids = shards["this"]

        # Cache
        self.cache_hits = 0
        self.cache_misses = 0

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
                presences=True,
                members=True,
            ),
            chunk_guilds_at_startup=not config.beta,
            guild_ready_timeout=10,
            max_messages=5000,
        )

        # Globals
        self._initialized: bool = False
        self.beta: bool = config.beta
        self.boottime: datetime.datetime = datetime.datetime.utcnow()
        self.created: bool = False
        self.logger: logging.Logger = logger
        # Cogs
        self._cogs: blink.CogStorage = blink.CogStorage()
        self.load_extension("cogs.pre-error")
        self.loadexceptions = []
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
            # "cogs.listing", why r lists so useless
            "cogs.sql",
            "cogs.social"
        ]
        self.startingcogs.append("jishaku")
        if not self.beta:  # Dont load these on beta as they will conflict with the live bot
            self.startingcogs.append("cogs.logging")
            self.startingcogs.append("cogs.stats")

        # Global channel cooldown - to avoid spamming commands
        self._cooldown:commands.CooldownMapping = commands.CooldownMapping.from_cooldown(
            5, 5.5, commands.BucketType.channel)
        log(f"Starting - {self.cluster}", "boot")

    def __repr__(self) -> str:
        return f"<Blink bot, cluster={repr(self.cluster)}, initialized={self._initialized}, since={self.boottime}>"

    def _trace(self) -> Dict[str, Union[str, int]]:
        """Debug information about the bot"""
        return {
            "prod": self.__class__.__qualname__,
            "beta": self.beta,
            "cluster": self.cluster.identifier,
            "cacherate": f"{self.cacherate()}%",
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

    # These are properties as they are static
    @property
    def colour(self) -> int:
        return 0xf5a6b9

    @property
    def default_prefixes(self) -> List[str]:
        # This is required to be a property because a standard attribute
        # would need to be copied to allow independent editing
        return [";", "b;", "B;", "blink"]

    def cacherate(self):
        """The percentage of cache reads that have hit the cache"""
        if self.cache_hits + self.cache_misses == 0:
            return 0
        else:
            return round((self.cache_hits / (self.cache_hits + self.cache_misses) * 100), 2)

    def dispatch(self, event: str, *args, **kwargs):
        """Overriding this stops events being sent to handlers before the bot is ready"""
        if self._initialized or "ready" in event:
            super().dispatch(event, *args, **kwargs)

    async def before_identify_hook(self, shard_id, *, initial=False):
        await asyncio.sleep(5)

    async def launch_shards(self):
        """
        Overriding this to stop shards launching and stepping on eachother
        This is necessary to abide by the 1 identify per 5s rate limit imposed by discord
        This is a overridden function of the library default but with clustering support
        """
        gateway = await self.http.get_gateway()

        self._connection.shard_count = self.shard_count
        self._connection.shard_ids = self.shard_ids

        # A is the first cluster and will not need to wait for the previous one to identify
        if not self.cluster.identifier == "A":
            await self.cluster.wait_cluster()
        for shard_id in self.shard_ids:
            log(f"Launching shard {shard_id}", "boot")
            await self.launch_shard(gateway, shard_id, initial=(shard_id == self.shard_ids[0]))

        # Tell other clusters that we have identified
        await self.cluster.ws.post_identify()
        self._connection.shards_launched.set()

    async def on_ready(self):
        """Creates the bot if the bot is ready for the first time"""
        if self._initialized:
            return
        self._initialized = True
        while len(self._init_shards) != len(self._shard_ids):
            await asyncio.sleep(1)  # Wait for all shards to be ready too...
        await self.create()

    async def on_shard_ready(self, id):
        log(f"Shard {id} ready", "ready")
        self._init_shards.add(id)

    async def on_shard_resume(self, id: int):
        """
        Change presence to the presence to the correct startup presence
        Presences are set to the presence set in __init__ when the bot
        reconencts a shard, so here after reconnecting we must change
        back to the shard specific status
        """
        if self._initialized:
            await self.change_presence(
                shard_id=id,
                status=discord.Status.online,
                activity=discord.Streaming(
                    name=f'b;help blinkbot.me [{self.cluster.identifier}{id}]',
                    url='https://www.twitch.tv/#'
                )
            )

    async def on_message(self, message: discord.Message):
        if not self.created:  # Events can be called after initialization but before creation
            return
        if message.author.bot:  # Bots dont execute commands
            return

        # blacklists
        async with self.cache_or_create("blacklist-global", "SELECT snowflakes FROM blacklist WHERE scope=$1", ("global",)) as blacklist:
            if message.author.id in blacklist.value["snowflakes"]:
                return  # Ignore all messages from users that are globally banned

        # create context
        # Cls is required for the custom context
        ctx = await self.get_context(message, cls=blink.Ctx)
        if not ctx:
            return  # Return on invalid commands

        # Invoke the context, passing it back to the internal handler
        await self.invoke(ctx)

    async def get_context(self, message: discord.Message, *, cls=commands.Context):
        ctx = await super().get_context(message, cls=cls)
        if not ctx.valid:
            return
        # Per channel cooldown to stop spamming of commands
        bucket = self._cooldown.get_bucket(message) # channel ratelimit
        # Tick the bucket only if the user is not a mod
        if not message.channel.permissions_for(message.author).manage_messages:
            if bucket.update_rate_limit():
                # React if permissions to do so or in (dms?)
                if not message.guild or message.channel.permissions_for(message.guild.me):
                    try:
                        await message.add_reaction("<:CHANNEL_COOLDOWN:785184949723594782>")
                    except discord.HTTPException:
                        pass
                return  # Dont invoke the command

        # Attaching guild data cache to context,
        # This is not done in the custom context definition because it needs to be run asynchronously
        if ctx.guild:
            data = self.cache_or_create(
                f"guild-{ctx.guild.id}", "SELECT data FROM guilds WHERE id=$1", (ctx.guild.id,))
            async with data:
                if not data.exists:
                    # Create a blank data entry for the guild
                    await self.DB.execute("INSERT INTO guilds VALUES ($1, $2)", ctx.guild.id, "{}")
                    await data.bot_invalidate(self)
            ctx.cache = data

        return ctx

    def load_extensions(self):
        """Load all extensions to the bot, catching and logging any errors"""
        for extension in self.startingcogs:
            try:
                self.load_extension(extension)
            except Exception as e:
                log(f"Unable to load: {extension} Exception was raised: {e}", "boot")
                self.loadexceptions.append(f"Unable to load: {extension} Exception was raised: {e}")

    async def invalidate_cache(self, scope: str, from_remote: bool = False):
        """
        Invalidate the local cache of a database entry
        Optionally tell other clusters to invalidate
        their cache if this cluster modified it
        """
        local = self._cache.get(scope)
        if local:
            # Cache will be fetched from database next time it is accessed on this cluster.
            local.invalidate()
        if not from_remote:
            await self.cluster.dispatch({"event": "INVALIDATE_CACHE", "cache": scope})

    def cache_or_create(self, identifier: str, statement: str, values: tuple) -> blink.DBCache:
        """Fetch a cached database entry or create a cache if not already cached"""
        if identifier.startswith("guild"):  # Guilds have custom classes because a guild value will always be a dict
            cls = blink.ServerCache
        else:
            cls = blink.DBCache

        if identifier in self._cache:
            self.cache_hits += 1
            return self._cache[identifier]  # Return local cache

        # Create new cache and add to local store
        cache = cls(self.DB, identifier, statement, values)
        self._cache[identifier] = cache
        self.cache_misses += 1
        return cache

    async def warn(self, message, shouldRaise=True):
        """
        Log a warning to the warnings discord channel
        Can raise an exception to back out of things if failure occurs
        """
        time = datetime.datetime.utcnow()
        message = f"{time.year}/{time.month}/{time.day} {time.hour}:{time.minute} [{self.cluster.identifier}/WARNING] {message}"
        await self.cluster.log_warns(message)
        if shouldRaise:
            raise blink.SilentWarning(message)

    async def create(self):
        """Do the initial setup of the bot after ready is called, this is only to be called once"""
        before = time.perf_counter()  # Performance metrics
        # Indicate to the cluster that the cache is ready and allow sending of statistics
        self.cluster._post.set()

        log("Waiting on clusters", "boot")

        await self.cluster.wait_until_ready()  # Wait on the other clusters to be ready
        await asyncio.sleep(self.cluster.index * 2)
        log(f"Waited {self.cluster.index * 2}s before starting", "boot")

        log(f"Clusters took {humanize.naturaldelta(time.perf_counter()-before,minimum_unit='microseconds')} to start", "boot")

        # DB
        self.DB = await asyncpg.create_pool(**{"user": "blink", "password": secrets.db, "database": "main", "host": config.db})
        self._cache = blink.CacheDict(1024)
        self.cache_or_create(
            "blacklist-global", "SELECT snowflakes FROM blacklist WHERE scope=$1", ("global",))

        # Misc
        self.session = aiohttp.ClientSession()  # TODO: localise sessions to cogs

        # Extensions
        self.unload_extension("cogs.pre-error")
        self.load_extensions()

        # Time taken for bot to be able to serve users
        boottime = datetime.datetime.utcnow() - self.boottime

        # Log boot metrics to the discord channel
        # TODO: this is ugly lol
        members = sum(1 for _ in self.get_all_members())
        boot = [
            '-' * 79,
            f"**BOT STARTUP:** {self.cluster.identifier} started at {datetime.datetime.utcnow()}",
            f"```STARTUP COMPLETED IN : {boottime} ({round(members / boottime.total_seconds(),2)} members / second)",
            f"GUILDS:{len(self.guilds)}",
            f"SHARDS:{len(self.shards)}```",
        ]
        if self.loadexceptions:
            boot.append("@everyone ***BOOT ERRORS***")
            boot = boot + self.loadexceptions

        self.bootlog = "\n".join(boot)
        if not self.beta:
            await self.cluster.log_startup(self.bootlog)

        # Signal that this function is done
        self.created = True

        log(f"Created in {humanize.naturaldelta(time.perf_counter()-before,minimum_unit='microseconds')}", "boot")
        log(f"This cluster start time was {humanize.naturaldelta(datetime.datetime.utcnow()- self.boottime)}", "boot")

        for id in self.shards:  # Set initial shard specific presence - this is different from the starting up presence set in __init__
            await self.change_presence(
                shard_id=id,
                status=discord.Status.online,
                activity=discord.Streaming(
                    name=f'b;help blinkbot.me [{self.cluster.identifier}{id}]',
                    url='https://www.twitch.tv/#'
                )
            )

        self.update_pres.start()  # This is still needed because idk ?????

    async def get_prefix(self, message: discord.Message) -> List[str]:
        """Custom prefixes"""
        if self.beta:  # Beta only beta prefix
            return ["beta;"]

        # Fetch the guild data from the cache
        async with self.cache_or_create(f"guild-{message.guild.id}", "SELECT data FROM guilds WHERE id=$1", (message.guild.id,)) as cache:
            if cache.value:
                prefixes = cache.value.get("prefixes") or self.default_prefixes
            else:
                prefixes = self.default_prefixes

        # Another array is required here to stop modifying the prefix array while iterating over it
        whitespace_prefixes = []

        for prefix in prefixes:
            whitespace_prefixes.append(prefix + " ")

        # It is important that whitespace prefixes come first due to a quirk in the library prefix code
        prefixes = whitespace_prefixes + prefixes

        return commands.when_mentioned_or(*prefixes)(self, message)

    @tasks.loop(hours=1)
    async def update_pres(self):
        """
        Loop runs every hour to ensure status is correct
        could be deprecated as status is no longer live
        """
        for id in self.shards:
            try:
                await self.change_presence(
                    shard_id=id,
                    status=discord.Status.online,
                    activity=discord.Streaming(
                        name=f'b;help blinkbot.me [{self.cluster.identifier}{id}]',
                        url='https://www.twitch.tv/#'
                    )
                )
            except Exception as e:
                await self.warn(f"Error occured in presence update {type(e)} `{e}`", False)

    async def cluster_event(self, payload: dict):
        """Handles messages coming from other clusters"""
        if payload is None:  # Ignore blank messages - this should be unreachable
            return
        # Close everthing possible and quit, this returns after stopping the loop because it raises an exception
        if payload["event"] == "SHUTDOWN":
            await self.stop()
        if payload["event"] == "RELOAD":
            # Reload cogs - sent by the dev reload command
            self.reload_extension(payload["cog"])

        if payload["event"] == "INVALIDATE_CACHE":
            # Purge local cache if remote invalidated it
            await self.invalidate_cache(payload.get("cache"), True)

    async def on_error(self, event_method: str, *_, **__):
        """Event error handler sends errors to github gist"""
        exc = sys.exc_info() # The current exception object
        tb = traceback.format_exc() # The traceback of the current exception
        embed = discord.Embed(colour=discord.Colour.red(),
                              title=f"{exc[0].__qualname__}")
        embed.set_author(name=f"Exception in event {event_method}")
        async with aiohttp.ClientSession() as cs: # Http session to post
            # Post exception data to github gists
            async with cs.post("https://api.github.com/gists", headers={"Authorization": "token " + secrets.gist}, json={"public": False, "files": {"traceback.txt": {"content": tb}}}) as gist:
                data = await gist.json()
                embed.description = data["html_url"] # Set the embed description to the url of the gist
            hook = discord.Webhook( # Create a new webhook client
                secrets.errorhook, adapter=discord.AsyncWebhookAdapter(cs))
            await hook.send(embed=embed, username=f"CLUSTER {self.cluster.identifier} EVENT ERROR") # Send the webhook to the error channel

    async def stop(self, cluster_up=True):
        """Close all internal loops and stop"""
        if cluster_up:
            await self.cluster.quit()
        await self.logout()
        await self.close()
        await self.loop.close()
        sys.exit(0)


async def launch(loop: asyncio.BaseEventLoop):
    """
    The main function to start the bot
    This is needed in an async environment to get the bot information from the cluster server
    This handles things like setting up logging, clustering, starting, and handling exceptions
    """
    cluster = clusters.Cluster(config.gateway) # Create a cluster object from the prescribed gateway
    # Start the internal loop of the cluster - connects to the master server
    cluster.start(loop)
    # wait for an identifier to be recieved from the gateway, the gateway will close if all clusters are active
    identifier = await cluster.wait_identifier()
    # Create logger based on the identifier for this cluster
    log = loggingSetup(identifier)
    bot = Blink(cluster, log)
    cluster.reg_bot(bot) # Cluster requires a bot object to function
    try:
        await bot.start(secrets.token, bot=True, reconnect=True)
    except KeyboardInterrupt: # close the bot on CTRL+C, it is proper practice to shutdown via the dev command
        await bot.logout()
        await cluster.quit()
        loop.close()
        sys.exit(1)
    except Exception as e:
        # Bot will report a crash to the master
        await cluster.crash(e, traceback.format_exc())
        print("Fatal client exception - exiting")
        await cluster.quit()
        loop.close()
        sys.exit(130)


if __name__ == "__main__":
    setupenv()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(launch(loop))
